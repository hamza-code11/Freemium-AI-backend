from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(plain_password, hashed_password)




from datetime import datetime, timedelta, timezone
import jwt

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )



from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import jwt

from app.core.config import SECRET_KEY, ALGORITHM

security = HTTPBearer()


def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return user_id

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )



import hashlib
import secrets
from uuid import uuid4


def create_refresh_token(
    session_id: str | None = None
) -> tuple[str, str, str]:

    session_id = session_id or str(uuid4())

    secret = secrets.token_urlsafe(48)

    refresh_token = f"{session_id}.{secret}"

    token_hash = hash_refresh_token(secret)

    return session_id, refresh_token, token_hash


def hash_refresh_token(secret: str) -> str:
    return hashlib.sha256(
        secret.encode("utf-8")
    ).hexdigest()