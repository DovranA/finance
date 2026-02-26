"""
Lightweight migration runner — zero extra dependencies (uses asyncpg only).

Usage:
    python sql/migrate.py upgrade
    python sql/migrate.py downgrade
    python sql/migrate.py status
    python sql/migrate.py upgrade <name>
    python sql/migrate.py downgrade <name>

Environment variables:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
    POSTGRES_USER, POSTGRES_PASSWORD
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg


# ── Paths ──────────────────────────────────────────────────────
SQL_DIR = Path(__file__).resolve().parent
ROOT_DIR = SQL_DIR.parent
UPGRADE_DIR = SQL_DIR / "upgrade"
DOWNGRADE_DIR = SQL_DIR / "downgrade"


# ── .env loader ────────────────────────────────────────────────
def _load_dotenv(path: Path) -> dict[str, str]:
    vars = {}
    if not path.is_file():
        return vars

    print(f"Loading environment variables from {path.name}...")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            vars[key.strip()] = value.strip().strip("\"'")
    return vars


combined_vars = {}
for env_filename in [".env", ".env.dev", ".env.local"]:
    combined_vars.update(_load_dotenv(ROOT_DIR / env_filename))

for key, value in combined_vars.items():
    if key not in os.environ:
        os.environ[key] = value


# ── DB connection ──────────────────────────────────────────────
def _dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "finance_db")
    user = os.getenv("POSTGRES_USER", "finance_user")
    password = os.getenv("POSTGRES_PASSWORD", "finance_secret")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


# ── Helpers ────────────────────────────────────────────────────
def _sorted_sql_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.sql"), key=lambda p: p.name)


def _choose_file(files: list[Path], title: str) -> str | None:
    if not files:
        print("No files available.")
        return None

    print(f"\n{title}")
    print("-" * 50)

    for idx, f in enumerate(files, start=1):
        print(f"{idx}. {f.name}")

    print("0. Cancel")

    while True:
        choice = input("Select number: ").strip()

        if not choice.isdigit():
            print("Enter a valid number.")
            continue

        choice = int(choice)

        if choice == 0:
            return None

        if 1 <= choice <= len(files):
            return files[choice - 1].name

        print("Out of range.")


async def _ensure_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name       TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )


async def _applied(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT name FROM schema_migrations ORDER BY name")
    return {r["name"] for r in rows}


# ── Commands ───────────────────────────────────────────────────
async def upgrade(target: str | None = None) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await _ensure_table(conn)
        applied = await _applied(conn)

        pending = [f for f in _sorted_sql_files(UPGRADE_DIR) if f.name not in applied]

        if not pending:
            print("Nothing to upgrade — all migrations applied.")
            return

        if target is None:
            target = _choose_file(pending, "Pending migrations:")
            if target is None:
                print("Cancelled.")
                return

        for sql_file in pending:
            sql = sql_file.read_text(encoding="utf-8")

            if not sql.strip():
                print(f"SKIP (empty) {sql_file.name}")
                continue

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (name) VALUES ($1)",
                    sql_file.name,
                )

            print(f"✔ Applied {sql_file.name}")

            if sql_file.name == target:
                break

        print("Upgrade complete.")

    finally:
        await conn.close()


async def downgrade(target: str | None = None) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await _ensure_table(conn)
        applied = await _applied(conn)

        if not applied:
            print("Nothing to downgrade — no migrations applied.")
            return

        all_downgrade = _sorted_sql_files(DOWNGRADE_DIR)

        to_rollback = [f for f in reversed(all_downgrade) if f.name in applied]

        if not to_rollback:
            print("No matching downgrade files found.")
            return

        if target is None:
            target = _choose_file(to_rollback, "Applied migrations (rollback):")
            if target is None:
                print("Cancelled.")
                return

        for sql_file in to_rollback:
            sql = sql_file.read_text(encoding="utf-8")

            async with conn.transaction():
                if sql.strip():
                    await conn.execute(sql)

                await conn.execute(
                    "DELETE FROM schema_migrations WHERE name = $1",
                    sql_file.name,
                )

            print(f"✔ Rolled back {sql_file.name}")

            if sql_file.name == target:
                break

        print("Downgrade complete.")

    finally:
        await conn.close()


async def status() -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await _ensure_table(conn)
        applied = await _applied(conn)
        all_files = _sorted_sql_files(UPGRADE_DIR)

        if not all_files and not applied:
            print("No migrations found.")
            return

        print(f"{'Status':<12} Migration")
        print("-" * 60)

        for f in all_files:
            mark = "applied" if f.name in applied else "pending"
            print(f"{mark:<12} {f.name}")

        file_names = {f.name for f in all_files}
        orphans = applied - file_names

        for name in sorted(orphans):
            print(f"{'orphan':<12} {name}")

    finally:
        await conn.close()


# ── CLI ────────────────────────────────────────────────────────
def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in (
        "upgrade",
        "downgrade",
        "status",
    ):
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "upgrade":
        asyncio.run(upgrade(target))
    elif command == "downgrade":
        asyncio.run(downgrade(target))
    elif command == "status":
        asyncio.run(status())


if __name__ == "__main__":
    main()
