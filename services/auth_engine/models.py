import enum
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserRole(str, enum.Enum):
    RIDER = "RIDER"
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RIDER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(String(50), index=True, nullable=False)
    vehicle_type = Column(String(30), default="UberX") # UberX, UberXL, UberBlack, Auto
    vehicle_number = Column(String(30), nullable=False)
    is_online = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True)
    geohash = Column(String(12), index=True, default="te7udw")
    lat = Column(String(20), default="19.0600")
    lon = Column(String(20), default="72.8350")
    rating = Column(String(10), default="4.92")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

