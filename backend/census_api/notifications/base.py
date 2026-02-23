from typing import Protocol

from ..enums import CensusRecordEvent
from ..models import CensusRecord


class Notifier(Protocol):
    async def send(self, *, event: CensusRecordEvent, record: CensusRecord) -> None: ...
