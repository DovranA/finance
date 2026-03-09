from fastapi import APIRouter


router = APIRouter(prefix="rule", tags=["Rule"])


@router.post("")
async def create_rule():
    pass
