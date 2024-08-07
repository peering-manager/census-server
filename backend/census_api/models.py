from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class CensusRecordBase(SQLModel):
    deployment_id: str = Field(primary_key=True, index=True)
    version: str
    python_version: str | None


class CensusRecord(CensusRecordBase, table=True):
    created_at: datetime
    updated_at: datetime
    country: str | None


class CensusRecordUpdate(CensusRecordBase):
    pass


class CensusSummary(BaseModel):
    label: str
    count: int
    percentage: float


class CensusSummaries(BaseModel):
    version: list[CensusSummary]
    python_version: list[CensusSummary]
    country: list[CensusSummary]
