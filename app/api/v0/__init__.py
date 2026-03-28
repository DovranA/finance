from fastapi import APIRouter, Depends

from app.api.v0.auth import require_jwt_bearer
from app.api.v0.routes import accounts, rule, statistics

PREFIX = "/v0"


router = APIRouter(prefix=PREFIX, dependencies=[Depends(require_jwt_bearer)])

router.include_router(accounts.router)
router.include_router(rule.router)
router.include_router(statistics.client_router)
router.include_router(statistics.admin_router)
