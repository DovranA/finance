"""Batch worker that pulls pending inbox actions from DB and applies rules."""

from __future__ import annotations

import argparse
import asyncio
import os
import time
import uuid
from pathlib import Path

from prometheus_client import start_http_server

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.metrics import AppMetrics, register_metrics
from app.di import create_container
from asyncpg import Pool
from app.infrastructure.db.transaction import transaction
from app.usecases.apply_rule_batch import BatchApplyRuleUseCase

logger = get_logger(__name__)


class RuleBatchWorker:
    """Processes pending DB inbox rows in periodic batches."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop = asyncio.Event()
        self._metrics: AppMetrics | None = None

    async def run(self) -> None:
        self._metrics = await register_metrics()
        container = create_container()

        async with container() as request_scope:
            pool = await request_scope.get(Pool)
            batch_uc = await request_scope.get(BatchApplyRuleUseCase)
            flush_task = asyncio.create_task(self._flush_loop(pool, batch_uc))
            cleanup_task = asyncio.create_task(self._cleanup_loop(pool))
            logger.info(
                "rule_batch_worker_started",
                interval_seconds=self._settings.batch.interval_seconds,
                batch_size=self._settings.batch.size,
                cleanup_days=self._settings.inbox_cleanup.cleanup_days,
                cleanup_interval=self._settings.inbox_cleanup.cleanup_interval,
            )

            await self._stop.wait()
            flush_task.cancel()
            cleanup_task.cancel()
            try:
                await flush_task
            except asyncio.CancelledError:
                pass
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass

    async def _flush_loop(
        self,
        pool: Pool,
        batch_uc: BatchApplyRuleUseCase,
    ) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(self._settings.batch.interval_seconds)
            await self._flush_once(pool, batch_uc)

    async def _cleanup_loop(self, pool: Pool) -> None:
        cleanup_days = self._settings.inbox_cleanup.cleanup_days
        cleanup_interval = self._settings.inbox_cleanup.cleanup_interval
        if cleanup_days <= 0 or cleanup_interval <= 0:
            logger.info(
                "inbox_cleanup_disabled",
                cleanup_days=cleanup_days,
                cleanup_interval=cleanup_interval,
            )
            return

        while not self._stop.is_set():
            await asyncio.sleep(cleanup_interval)
            try:
                deleted_count = await self._cleanup_processed_rows(pool)
                logger.info(
                    "inbox_cleanup_completed",
                    cleanup_days=cleanup_days,
                    deleted_count=deleted_count,
                )
            except Exception:
                logger.exception(
                    "inbox_cleanup_failed",
                    cleanup_days=cleanup_days,
                    cleanup_interval=cleanup_interval,
                )

    async def _cleanup_processed_rows(self, pool: Pool) -> int:
        cleanup_days = self._settings.inbox_cleanup.cleanup_days
        async with transaction(pool) as conn:
            result: str = await conn.execute(
                "DELETE FROM rule_action_inbox "
                "WHERE status = 'processed' "
                "AND processed_at IS NOT NULL "
                "AND processed_at < NOW() - ($1 * INTERVAL '1 day')",
                cleanup_days,
            )
        return int(result.split()[-1])

    async def _flush_once(
        self,
        pool: Pool,
        batch_uc: BatchApplyRuleUseCase,
    ) -> None:
        flush_started_at = time.perf_counter()
        rows = await self._claim_pending_rows(pool, self._settings.batch.size)
        if not rows:
            if self._metrics is not None:
                self._metrics.inc_inbox_batch_run("empty")
            return

        grouped: dict[str, list[dict]] = {}
        for row in rows:
            event_code = row["event_code"]
            grouped.setdefault(event_code, []).append(
                {
                    "inbox_id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "event_id": str(row["event_id"]),
                    "role": row["role"],
                    "metadata": row["metadata"] or {},
                }
            )

        for event_code, items in grouped.items():
            started_at = time.perf_counter()
            try:
                result = await batch_uc.execute(event_code=event_code, items=items)
                await self._mark_batch_result(pool, result)
            except Exception:
                if self._metrics is not None:
                    self._metrics.inc_inbox_batch_run("failed")
                raise

            if self._metrics is not None:
                self._metrics.observe_inbox_batch_duration(
                    event_code=event_code,
                    duration_seconds=time.perf_counter() - started_at,
                )
                self._metrics.inc_inbox_batch_run("success")

                for item in result.get("results", []):
                    if item.get("applied"):
                        stage = "applied"
                    elif item.get("skipped_duplicate"):
                        stage = "duplicate_skipped"
                    else:
                        stage = "apply_failed"
                    self._metrics.inc_inbox_events(stage, event_code)

            logger.info(
                "rule_batch_flushed",
                event_code=event_code,
                total=result["total"],
                applied=result["applied"],
                skipped=result.get("skipped", 0),
                failed=result["failed"],
            )

        if self._metrics is not None:
            self._metrics.observe_inbox_batch_duration(
                event_code="all",
                duration_seconds=time.perf_counter() - flush_started_at,
            )

    async def _claim_pending_rows(self, pool: Pool, size: int):
        async with transaction(pool) as conn:
            return await conn.fetch(
                "WITH picked AS ("
                "  SELECT id FROM rule_action_inbox "
                "  WHERE status = 'pending' "
                "  ORDER BY created_at ASC "
                "  LIMIT $1 "
                "  FOR UPDATE SKIP LOCKED"
                ") "
                "UPDATE rule_action_inbox i "
                "SET status = 'processing' "
                "FROM picked "
                "WHERE i.id = picked.id "
                "RETURNING i.id, i.event_id, i.event_code, i.user_id, i.role, i.metadata",
                size,
            )

    async def _mark_batch_result(self, pool: Pool, result: dict) -> None:
        async with transaction(pool) as conn:
            for item in result.get("results", []):
                inbox_id = item.get("inbox_id")
                if not inbox_id:
                    continue
                if item.get("applied"):
                    await conn.execute(
                        "UPDATE rule_action_inbox "
                        "SET status = 'processed', processed_at = NOW(), error = NULL "
                        "WHERE id = $1",
                        uuid.UUID(inbox_id),
                    )
                elif item.get("skipped_duplicate"):
                    await conn.execute(
                        "UPDATE rule_action_inbox "
                        "SET status = 'processed', processed_at = NOW(), error = $2 "
                        "WHERE id = $1",
                        uuid.UUID(inbox_id),
                        item.get("error"),
                    )
                else:
                    await conn.execute(
                        "UPDATE rule_action_inbox "
                        "SET status = 'failed', processed_at = NOW(), error = $2 "
                        "WHERE id = $1",
                        uuid.UUID(inbox_id),
                        item.get("error"),
                    )


async def run_worker() -> None:
    # Setup logging first with default level, then load settings
    setup_logging("INFO")
    settings = get_settings()
    # Update logging level based on settings
    setup_logging(settings.app.log_level)

    worker = RuleBatchWorker()

    if worker._settings.app.enable_metrics and worker._settings.app.metrics_port:
        start_http_server(worker._settings.app.metrics_port)
        logger.info(
            "worker_metrics_server_started",
            worker="batch_worker",
            port=worker._settings.app.metrics_port,
        )

    await worker.run()


def _load_env_file(path: str) -> None:
    env_path = Path(path)
    if not env_path.is_absolute():
        env_path = Path.cwd() / env_path

    if not env_path.exists():
        logger.debug(f"Environment file not found at {env_path}, using container env")
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            os.environ[key] = value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run rule batch worker in standalone mode.",
    )
    parser.add_argument(
        "--env-file",
        default="",
        help="Optional path to env file to load before starting worker",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.env_file:
        _load_env_file(args.env_file)
    asyncio.run(run_worker())
