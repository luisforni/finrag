from abc import ABC, abstractmethod
from uuid import UUID

from finrag_core.domain.models.user import UserCreate, UserInDB


class AbstractUserRepository(ABC):
    @abstractmethod
    async def create(self, data: UserCreate) -> UserInDB: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> UserInDB | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> UserInDB | None: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...
