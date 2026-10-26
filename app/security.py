import datetime as dt
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.db import DbDep, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

BCRYPT_MAX_BYTES = 72  # o bcrypt 5 recusa senhas acima disso em vez de truncar


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode()
    if len(raw) > BCRYPT_MAX_BYTES:
        return False  # senha inválida, não erro 500
    return bcrypt.checkpw(raw, password_hash.encode())


def create_token(user_id: int) -> str:
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbDep) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # `algorithms` fixo: impede confusão de algoritmo (ex.: token com alg=none)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


UserDep = Annotated[User, Depends(current_user)]