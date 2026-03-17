import pytest

from finrag_core.domain.models.user import UserCreate, UserRole
from finrag_core.services.user_service import UserService


@pytest.fixture
def service(mock_user_repo):
    return UserService(repository=mock_user_repo)


class TestRegister:
    async def test_successful_registration(self, service, mock_user_repo, sample_user_in_db):
        mock_user_repo.exists_by_email.return_value = False
        mock_user_repo.create.return_value = sample_user_in_db

        result = await service.register(
            UserCreate(email="new@bank.com", full_name="New User", password="securepass123")
        )
        assert result.id == sample_user_in_db.id

    async def test_duplicate_email_raises(self, service, mock_user_repo):
        mock_user_repo.exists_by_email.return_value = True
        with pytest.raises(ValueError, match="already registered"):
            await service.register(
                UserCreate(email="dup@bank.com", full_name="Dup", password="pass12345")
            )


class TestAuthenticate:
    async def test_correct_credentials(self, service, mock_user_repo, sample_user_in_db):
        mock_user_repo.get_by_email.return_value = sample_user_in_db
        result = await service.authenticate("analyst@bank.com", "password123")
        assert result.id == sample_user_in_db.id

    async def test_wrong_password_raises(self, service, mock_user_repo, sample_user_in_db):
        mock_user_repo.get_by_email.return_value = sample_user_in_db
        with pytest.raises(ValueError, match="Invalid credentials"):
            await service.authenticate("analyst@bank.com", "wrongpass")

    async def test_unknown_email_raises(self, service, mock_user_repo):
        mock_user_repo.get_by_email.return_value = None
        with pytest.raises(ValueError, match="Invalid credentials"):
            await service.authenticate("nobody@bank.com", "pass")
