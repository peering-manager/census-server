from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Header, Query

from ...core.dependencies import SessionDep
from ...crud import records as crud
from ...models import CensusRecord, CensusRecordUpdate, CensusSummaries
from ...services.records import process_census_report

router = APIRouter()


@router.post("/", response_model=CensusRecord)
async def create_record(
    *,
    session: SessionDep,
    record: CensusRecordUpdate,
    real_ip: Annotated[str | None, Header(alias="X-Real-IP")] = None,
) -> CensusRecord:
    return await process_census_report(session=session, record=record, real_ip=real_ip)


@router.get("/", response_model=list[CensusRecord])
async def read_records(
    *,
    session: SessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> Sequence[CensusRecord]:
    return await crud.get_records(session=session, offset=offset, limit=limit)


@router.get("/summary", response_model=CensusSummaries)
async def read_summary(*, session: SessionDep) -> CensusSummaries:
    return await crud.get_summary(session=session)
