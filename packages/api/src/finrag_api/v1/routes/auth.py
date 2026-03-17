from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel

from finrag_core.core.config import get_settings
from finrag_core.domain.models.user import UserCreate, UserRole
from finrag_core.services.audit_service import AuditAction, AuditService
from finrag_core.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def get_user_service() -> UserService:
    raise NotImplementedError("UserService not configured")


def get_audit_service() -> AuditService:
    return AuditService()


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.ANALYST


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    try:
        user = await user_service.register(
            UserCreate(
                email=req.email,
                full_name=req.full_name,
                password=req.password,
                role=req.role,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    audit.log(AuditAction.USER_REGISTER, user.id)
    return {"message": "User registered", "user_id": str(user.id)}


@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserService, Depends(get_user_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Token:
    try:
        user = await user_service.authenticate(form_data.username, form_data.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    audit.log(AuditAction.USER_LOGIN, user.id)

    user_claims = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }
    payload = {
        "sub": str(user.id),
        "user": user_claims,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return Token(access_token=token, token_type="bearer")
