from abc import ABC, abstractmethod
from uuid import UUID

from finrag_core.domain.models.query_log import QueryLog, QueryLogCreate


class AbstractQueryLogRepository(ABC):
    @abstractmethod
    async def create(self, data: QueryLogCreate) -> QueryLog: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID, limit: int, offset: int) -> list[QueryLog]: ...
