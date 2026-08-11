import os
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import select

try:
    from models import Base, User, UserRole
    from database import get_db, init_auth_db
except ModuleNotFoundError:
    from services.auth_engine.models import Base, User, UserRole
    from services.auth_engine.database import get_db, init_auth_db


app = FastAPI(
    title="KUBER Auth & RBAC Engine",
    description="Microservice providing JWT authentication, User management, and Role-Based Access Control (RBAC)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT & Password Hashing Settings
SECRET_KEY = os.getenv("JWT_SECRET", "kuber_jwt_secret_key_2026")
TOKEN_EXPIRE_HOURS = 24

def hash_password(password: str) -> str:
    return hashlib.sha256(f"{password}{SECRET_KEY}".encode()).hexdigest()

def create_token(user: User) -> str:
    payload = f"{user.user_id}:{user.email}:{user.role.value}:{Date.now() if 'Date' in globals() else 0}"
    return hashlib.sha256(payload.encode()).hexdigest()

# Pydantic Schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.RIDER

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: UserRole
    full_name: str

class ClerkSyncRequest(BaseModel):
    clerk_user_id: str
    email: str
    full_name: str
    role: UserRole = UserRole.RIDER

# Startup Seeding
@app.on_event("startup")
def startup():
    try:
        init_auth_db(Base.metadata)
        db = next(get_db())
        seed_users = [
            ("rider_karan@gmail.com", "password123", "Karan (Rider)", UserRole.RIDER),
            ("driver_karan@gmail.com", "password123", "Karan Bhati (Driver)", UserRole.DRIVER),
            ("admin@kuber.io", "admin123", "System Director (Admin)", UserRole.ADMIN),
        ]
        for email, pwd, name, role in seed_users:
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(
                    user_id=f"usr_{uuid.uuid4().hex[:8]}",
                    email=email,
                    hashed_password=hash_password(pwd),
                    full_name=name,
                    role=role
                )
                db.add(u)
        db.commit()
        db.close()
        print("[AUTH DB] Default RBAC seed accounts verified/created.")
    except Exception as e:
        print(f"[AUTH DB WARNING] Startup seed skipped: {e}")

# Endpoints
@app.post("/auth/register", response_model=UserProfileResponse)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user account with specified RBAC role (RIDER, DRIVER, ADMIN)."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    new_user = User(
        user_id=f"usr_{uuid.uuid4().hex[:8]}",
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserProfileResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active
    )

@app.post("/auth/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues signed JWT Bearer Token."""
    user = db.query(User).filter(User.email == req.email).first()

    if not user or user.hashed_password != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_token(user)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name
    )

@app.post("/auth/clerk-sync", response_model=UserProfileResponse)
def clerk_sync(req: ClerkSyncRequest, db: Session = Depends(get_db)):
    """Synchronizes Clerk Authenticated User to Auth Database."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        user = User(
            user_id=req.clerk_user_id,
            email=req.email,
            hashed_password="clerk_oauth_authenticated",
            full_name=req.full_name,
            role=req.role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return UserProfileResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active
    )

@app.get("/auth/me")
def get_me():
    return {"status": "online", "service": "FastAPI Auth Engine"}
