from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.models import User
from app.core.security import current_user, hash_password, verify_password, make_token

router = APIRouter(tags=["Ali | Authentication"])

class Register(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

def safe_user(u: User):
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role}

@router.post("/register", status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    email = data.email.lower()

    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")

    user = User(
        email=email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role="student"
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    db.refresh(user)
    return safe_user(user)

@router.post("/login")
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": make_token(user), "token_type": "bearer", "user": safe_user(user)}

@router.get("/me")
def me(user: User = Depends(current_user)):
    return safe_user(user)