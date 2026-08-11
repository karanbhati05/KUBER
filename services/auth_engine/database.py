import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Standard built-in SQLite database engine requiring zero external driver dependencies
DATABASE_URL = os.getenv("MYSQL_MUMBAI_URL")

if not DATABASE_URL or "mysql" in DATABASE_URL:
    DATABASE_URL = "sqlite:///./kuber_auth.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_auth_db(metadata):
    try:
        metadata.create_all(bind=engine)
        print("[AUTH DB] User and RBAC tables initialized successfully.")
    except Exception as e:
        print(f"[AUTH DB WARNING] Database schema check: {e}")
