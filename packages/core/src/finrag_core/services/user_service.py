from finrag_core.core.logging import get_logger
from finrag_core.core.security import hash_password, verify_password
from finrag_core.domain.interfaces.user_repository import AbstractUserRepository
from finrag_core.domain.models.user import User, UserCreate, UserInDB

logger = get_logger(__name__)


class UserService:
    def __init__(self, repository: AbstractUserRepository) -> None:
        self._repo = repository

    async def register(self, data: UserCreate) -> UserInDB:
        if await self._repo.exists_by_email(data.email):
            raise ValueError(f"Email already registered: {data.email}")
        user = await self._repo.create(data)
        logger.info("user_registered", user_id=str(user.id), email=user.email, role=user.role)
        return user

    async def authenticate(self, email: str, password: str) -> UserInDB:
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account is disabled")
        logger.info("user_authenticated", user_id=str(user.id), email=email)
        return user

    async def get_by_id(self, user_id) -> User | None:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            return None
        return User.model_validate(user.model_dump())
