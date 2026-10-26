from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import select

from app.db import DbDep, User
from app.security import BCRYPT_MAX_BYTES, create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Usado quando o e-mail não existe: o tempo de resposta fica igual ao de uma senha errada.
_DUMMY_HASH = hash_password("timing-equalizer")


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)

    @field_validator("password")
    @classmethod
    def _fits_bcrypt(cls, value: str) -> str:
        # 72 caracteres com acentos podem passar de 72 bytes; o limite do bcrypt é em bytes
        if len(value.encode()) > BCRYPT_MAX_BYTES:
            raise ValueError(f"password must be at most {BCRYPT_MAX_BYTES} bytes")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — é o tipo do token (RFC 6750), não um segredo


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(data: RegisterIn, db: DbDep) -> User:
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbDep) -> TokenOut:
    user = db.scalar(select(User).where(User.email == form.username))
    password_ok = verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok:
        # Mesma mensagem para e-mail inexistente e senha errada: evita enumeração de usuários
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenOut(access_token=create_token(user.id))
