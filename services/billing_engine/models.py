from sqlalchemy import Column , Integer , String , Float , DateTime , Enum
from sqlalchemy.ext.declarative import declarative_base
import enum
import datetime

Base = declarative_base()

class TripStatus(enum.Enum):
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key = True, index = True)
    trip_id = Column(String(50), unique=True, index=True, nullable=False) # This one SHOULD be unique
    rider_id = Column(String(50), nullable=False)
    driver_id = Column(String(50), nullable=False)
    
    start_lat = Column(Float , nullable = False)
    start_lon = Column(Float , nullable = False)
    end_lat = Column(Float , nullable = True)
    end_lon = Column(Float , nullable = True)

    distance_km = Column(Float , nullable=True)
    fare_amount = Column(Float , nullable = True)

    status = Column(Enum(TripStatus), nullable = False , default = TripStatus.COMPLETED)
    created_at = Column(DateTime , default = datetime.datetime.utcnow)
    
    