from fastapi import APIRouter
from app.api.v0.routes import accounts, rule, statistics

PREFIX = "/v0"


router = APIRouter(prefix=PREFIX)

router.include_router(accounts.router)
router.include_router(rule.router)
router.include_router(statistics.client_router)
router.include_router(statistics.admin_router)
