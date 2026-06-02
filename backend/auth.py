from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


def hash_password(p: str) -> str:
    return pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return pwd.verify(p, h)
    except Exception:
        return False


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=settings.JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


def require_parent(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    if payload.get("role") != "parent":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parent only")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_only_child(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the child from the JWT issued at /api/auth/enter.

    Despite the legacy name, this app supports multiple children — each gets
    a token at /enter and every /api/child/* call must carry it so the right
    child's data is loaded. (Was returning .first() across all children, which
    quietly sent Anvi's traffic to Samihan's data.)"""
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    if payload.get("role") != "child":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Child only")
    user = db.get(User, int(payload["sub"]))
    if not user or user.role != "child":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_only_parent(db: Session) -> User:
    parent = db.query(User).filter(User.role == "parent").first()
    if not parent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No parent user seeded")
    return parent
