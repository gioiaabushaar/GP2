from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .db import get_db
from .models import User
from .config import settings

hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

def hash_password(value: str) -> str:
    return hasher.hash(value)

def verify_password(value: str, hashed: str) -> bool:
    return hasher.verify(value, hashed)

def make_token(user: User) -> str:
    payload = {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.nexis_token_minutes)}
    return jwt.encode(payload, settings.nexis_secret_key, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")
    try:
        payload = jwt.decode(credentials.credentials, settings.nexis_secret_key, algorithms=["HS256"])
        uid = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account unavailable")
    return user

def instructor(user: User = Depends(current_user)) -> User:
    if user.role != "instructor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Instructor access required")
    return user