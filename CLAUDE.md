# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Finance microservice for the TMBIZ platform (TikTok-like app). Manages user
financial accounts, an append-only ledger, a rule/reward engine, transfers,
and competition statistics. Python 3.12, FastAPI + asyncpg, Dishka DI, Clean
/ Hexagonal architecture. Also exposes a gRPC server and consumes several
RabbitMQ queues.

## Commands

```bash
# Activate venv (Windows)
venv\Scripts\Activate.ps1

# Install deps (there is only one requirements file — no separate dev reqs)
pip install -r requirements.txt

# Run the API server (also starts gRPC server + RabbitMQ consumers via lifespan)
uvicorn app.main:app --reload

# Run migrations (custom zero-dependency runner, reads .env/.env.dev directly)
python sql/migrate.py upgrade
python sql/migrate.py downgrade
python sql/migrate.py status

# Tests (pytest + pytest-asyncio + pytest-mock are installed; there is no
# pytest.ini, so async tests must be marked explicitly or awaited via
# pytest-asyncio's default strict mode — check how a neighboring test does it
# before adding a new async test)
pytest
pytest tests/unit/domain/test_account.py
pytest tests/unit/domain/test_account.py::test_credit

# Regenerate gRPC/protobuf code from the event-schemas submodule
python -m grpc_tools.protoc --proto_path=event-schemas --python_out=app/domain/event_schemas \
  --pyi_out=app/domain/event_schemas --grpc_python_out=app/domain/event_schemas \
  event-schemas/finance.proto
```

Infrastructure (Postgres, Redis, RabbitMQ) is defined in `docker/docker-compose.yml`.
`event-schemas/` is a git submodule (`git submodule update --init`) containing
the shared `.proto` definitions for finance/competition/user events.

Note: `tests/integration/api/test_account_endpoints.py` imports from
`app.api.routes` / `app.api.schemas`, but the actual package is
`app.api.v0.routes` / `app.api.v0.schemas` — that test predates the `v0`
API restructuring and is currently broken. Don't copy its import paths.

## Architecture

Clean/Hexagonal architecture, dependencies point inward only:

```
API (FastAPI routes) → Use Cases → Domain (entities, value objects, repo interfaces) ← Infrastructure (Postgres/Redis/RabbitMQ/REST)
```

- `app/domain/` has zero infrastructure imports. Repositories here
  (`app/domain/repositories/*.py`) are abstract interfaces (ports);
  concrete implementations live under `app/infrastructure/db/repositories/`.
- `app/usecases/` orchestrate domain logic with injected repos/cache — one
  class per use case (e.g. `GetBalanceUseCase`, `TransferUseCase`,
  `ApplyRuleUseCase`).
- `app/api/v0/` is the presentation layer: routes in
  `app/api/v0/routes/{accounts,rule,statistics,super_admin}.py`, request/response
  schemas in `app/api/v0/schemas/`. All `/api/v0/*` routes require a JWT
  bearer token via `require_jwt_bearer` (`app/api/v0/auth.py`), enforced as a
  router-level dependency in `app/api/v0/__init__.py`.
- `app/di.py` wires everything through Dishka: `ConfigProvider` and
  `InfrastructureProvider`/`RepositoryProvider`/`PolicyProvider` are
  `Scope.APP` (singletons for app lifetime — pool, redis, cache, repos,
  condition engine), `UseCaseProvider` is `Scope.REQUEST` (one instance per
  HTTP request).
- `app/main.py` is the composition root: builds the FastAPI app, registers
  the Dishka container, mounts Prometheus metrics, registers domain
  exception → HTTP status handlers, and (in `lifespan`) starts/stops the
  gRPC server plus five RabbitMQ consumer background tasks and two periodic
  background loops (DB metrics collector, competition-snapshot freezer).

### Money & ledger

- All monetary amounts are `BIGINT` — never floats. `Money`
  (`app/domain/value_objects/money.py`) wraps amount+currency and refuses
  cross-currency arithmetic (`CurrencyMismatch`).
- `LedgerEntry` is a frozen dataclass; the ledger table is append-only
  (never updated/deleted) — it's the audit trail.
- Balance mutations use raw SQL (`asyncpg`, no ORM) so they can rely on
  `SELECT ... FOR UPDATE` and atomic `UPDATE ... SET balance = balance - $1
  WHERE balance >= $1` guards, plus custom migrations.
- Idempotency keys (`app/domain/entities/idempotency_key.py`) give
  at-most-once semantics for financial operations under retries.

### Rule / policy engine

Business rules (`app/domain/entities/rule.py`) are CRUD'd via
`app/usecases/rule_crud.py` and applied via `ApplyRuleUseCase` /
`BatchApplyRuleUseCase`. A rule has `conditions` (validated by the policy
engine) and `actions` (direction/amount/currency, optionally
`target_users`/`target_amounts` to split a reward across multiple parties,
e.g. a video's actor and author).

Conditions are evaluated by `ConditionEngine`
(`app/domain/policies/engine.py`), which looks up each condition key in a
`ValidatorRegistry` and calls `validator.validate(...)`. Built-in validators
live in `app/domain/policies/validators/`: `min_balance`, `role_required`,
`daily_limit`, `cooldown_days`, `one_time_only`, `required_metadata`,
`view_percentage`, `dynamic_amount`. To add a new condition type, implement
`ConditionValidator` (`app/domain/policies/base.py`) and register it in
`PolicyProvider.get_registry` in `app/di.py` — the engine dispatches purely
by the condition's dict key, so nothing else needs to change.

See `docs/rule-endpoints.md` for the full request/response shape of the rule
API (this is the most current, detailed reference for that surface).

### Event flow (RabbitMQ)

Five independent consumers, each independently toggleable via
`APP_ENABLE_*_CONSUMER` settings and started as a background task in
`app/main.py` lifespan: inbox (reward events → applied via the rule engine,
see `app/usecases/inbox_service.py` + `app/infrastructure/rabbitmq/inbox_consumer.py`),
competition, user-registered, user-deleted, user-blocked. Each has its own
DTO parser under `app/infrastructure/rabbitmq/dto_parser_*.py`. Queue names
and the prefetch count are configured in `RabbitMQSettings`
(`app/core/config.py`). `app/infrastructure/rabbitmq/batch_worker.py` and
`app/usecases/apply_rule_batch.py` / `set_balance_batch.py` handle
high-throughput batch application of rules/balance changes.

### Competitions

`app/usecases/competition_service.py` + `AdminStatisticsUseCase` maintain a
leaderboard that gets **frozen** at a configured instant
(`COMPETITION_FREEZE_DATETIME` in `app/core/config.py`): a background loop in
`app/main.py` (`_freeze_competition_snapshot`) checks once past that
datetime whether a snapshot refresh is needed and, if so, calls
`freeze_competition_snapshot(currency=...)` to persist final
rank/balance so results stop changing after the deadline.

### Config

All settings are env-driven via `pydantic-settings`, grouped by prefix in
`app/core/config.py` (`POSTGRES_`, `RABBITMQ_`, `REDIS_`, `APP_`, `BATCH_`,
`INBOX_`, `OUTBOX_`, `REST_API_`, `USER_MANAGEMENT_`, `JWT_`,
`COMPETITION_`). `get_settings()` is `lru_cache`d — settings are parsed once
per process. See `.env.example` for the full variable list.

### Redis is optional

`InfrastructureProvider.get_redis` swallows connection failures and yields
`None`; `CacheService` and everything downstream is typed `CacheService |
None` and must degrade to cache-misses rather than erroring when Redis is
unavailable — don't add code that assumes Redis is always present.

### gRPC

`app/grpc_server.py` runs alongside the HTTP API (started/stopped in the
same `main.py` lifespan) using proto-generated code in
`app/domain/event_schemas/` (generated from the `event-schemas` submodule —
regenerate with the `protoc` command above after changing a `.proto` file,
don't hand-edit the generated `*_pb2*.py` files).

## Docs

`docs/` has more detail than this file for specific subsystems — check it
before re-deriving something from source:
`architecture.md`, `domain-model.md`, `infrastructure.md`, `configuration.md`,
`database.md`, `testing.md`, `api-reference.md`, `rule-endpoints.md`,
`deployment.md`. Note `architecture.md`'s "Current State & Roadmap" section
and its project-structure listing predate a lot of what's now implemented
(rules, competitions, statistics, transfers, superadmin, gRPC, five RabbitMQ
consumers) — trust the source tree over that section.
