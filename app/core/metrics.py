"""Application metrics backed by prometheus_client."""

from __future__ import annotations

from asyncio import Lock

from asyncpg import Pool
from prometheus_client import Counter, Gauge, Histogram


class AppMetrics:
    """Prometheus metrics for HTTP requests and DB pool state."""

    def __init__(self) -> None:
        self.response_latency = Histogram(
            "http_response_duration_seconds",
            "Histogram of response latencies",
            ["path", "method", "status"],
        )
        self.requests_total = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["path", "method", "status"],
        )

        self.db_pool_conns = Gauge(
            "db_pool_conns",
            "Number of connections in the pool by state (total, idle, acquired, max)",
            ["state"],
        )
        self.db_pool_acquire_count = Gauge(
            "db_pool_acquire_count",
            "Cumulative count of pool stats samples (asyncpg does not expose acquire count)",
        )
        self.db_pool_acquire_duration = Gauge(
            "db_pool_acquire_duration_seconds",
            "Cumulative duration of acquisitions (not exposed by asyncpg pool stats)",
        )
        self.db_pool_wait_count = Gauge(
            "db_pool_wait_count",
            "Cumulative count of waits (not exposed by asyncpg pool stats)",
        )
        self.db_pool_wait_duration = Gauge(
            "db_pool_wait_duration_seconds",
            "Cumulative wait duration (not exposed by asyncpg pool stats)",
        )
        self.db_active_connections = Gauge(
            "db_active_connections",
            "Number of active connections by user and application",
            ["usename", "application_name"],
        )

        self._sample_count = 0

    def observe_latency(
        self,
        path: str,
        method: str,
        status_code: str,
        duration_seconds: float,
    ) -> None:
        self.response_latency.labels(
            path=path,
            method=method,
            status=status_code,
        ).observe(duration_seconds)

    def inc_request(self, path: str, method: str, status_code: str) -> None:
        self.requests_total.labels(
            path=path,
            method=method,
            status=status_code,
        ).inc()

    async def record_db_stats(self, pool: Pool | None) -> None:
        if pool is None:
            return

        total = pool.get_size()
        idle = pool.get_idle_size()
        acquired = max(total - idle, 0)
        max_size = pool.get_max_size()

        self.db_pool_conns.labels(state="total").set(float(total))
        self.db_pool_conns.labels(state="idle").set(float(idle))
        self.db_pool_conns.labels(state="acquired").set(float(acquired))
        self.db_pool_conns.labels(state="max").set(float(max_size))

        self._sample_count += 1
        self.db_pool_acquire_count.set(float(self._sample_count))
        self.db_pool_acquire_duration.set(0.0)
        self.db_pool_wait_count.set(0.0)
        self.db_pool_wait_duration.set(0.0)

        await self._record_active_connections(pool)

    async def _record_active_connections(self, pool: Pool) -> None:
        query = (
            "SELECT usename, COALESCE(application_name, '') AS application_name, COUNT(*) AS cnt "
            "FROM pg_stat_activity "
            "WHERE datname = current_database() AND state = 'active' "
            "GROUP BY usename, application_name"
        )
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

        self.db_active_connections.clear()
        for row in rows:
            usename = row["usename"] or ""
            app_name = row["application_name"] or ""
            self.db_active_connections.labels(
                usename=usename,
                application_name=app_name,
            ).set(float(row["cnt"]))


_metrics_instance: AppMetrics | None = None
_metrics_lock = Lock()


async def register_metrics() -> AppMetrics:
    """Initialize metrics once and return singleton instance."""
    global _metrics_instance

    if _metrics_instance is not None:
        return _metrics_instance

    async with _metrics_lock:
        if _metrics_instance is None:
            _metrics_instance = AppMetrics()

    return _metrics_instance
