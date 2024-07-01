from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import select

from ...core.dependencies import SessionDep

router = APIRouter()


@router.get("/", response_model=dict[str, Any])
async def get_health(*, session: SessionDep) -> JSONResponse:
    result = await session.exec(select(1))
    result.close()

    return JSONResponse(content={"ok": True})
