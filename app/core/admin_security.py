import jwt  # PyJWT
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY, ALGORITHM
from app.core.database import get_db
from app.repositories.admin_repository import AdminRepository

bearer_scheme = HTTPBearer()


def get_current_admin(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token"
    )

    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise unauthorized

    sub = str(payload.get("sub", ""))

    if payload.get("role") != "admin" or not sub.startswith("admin:"):
        raise unauthorized

    try:
        admin_id = int(sub.split(":", 1)[1])
    except ValueError:
        raise unauthorized

    admin = AdminRepository.get_by_id(db, admin_id)
    if not admin:
        raise unauthorized

    return admin
