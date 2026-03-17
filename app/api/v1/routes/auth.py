from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

# In-memory user store for demo — replace with DB in production
_DEMO_USERS: dict[str, dict] = {}


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.ANALYST


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest) -> dict:
    if req.email in _DEMO_USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    import uuid
    from datetime import datetime, timezone

    user_id = uuid.uuid4()
    _DEMO_USERS[req.email] = {
        "id": str(user_id),
        "email": req.email,
        "full_name": req.full_name,
        "role": req.role.value,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hashed_password": hash_password(req.password),
    }
    return {"message": "User registered", "user_id": str(user_id)}


@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user_data = _DEMO_USERS.get(form_data.username)
    if not user_data or not verify_password(form_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Embed user claims into token (OWASP A01 — role-based access)
    user_claims = {k: v for k, v in user_data.items() if k != "hashed_password"}
    token = create_access_token(
        subject=user_data["id"],
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    # Re-encode with user claims
    from datetime import datetime, timezone

    from jose import jwt

    payload = {
        "sub": user_data["id"],
        "user": user_claims,
        "exp": (
            datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        ),
    }
    access_token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return Token(access_token=access_token, token_type="bearer")
