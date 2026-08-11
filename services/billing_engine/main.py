import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:
    from models import Base, Trip, TripStatus
    from database import resolve_shard_key, get_db_for_shard, init_shard_databases
except ModuleNotFoundError:
    from services.billing_engine.models import Base, Trip, TripStatus
    from services.billing_engine.database import resolve_shard_key, get_db_for_shard, init_shard_databases


app = FastAPI(
    title="KUBER Billing Engine",
    description="Handles fare calculation and sharded trip storage across geographic databases"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TripCompletionRequest(BaseModel):
    rider_id: str
    driver_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    distance_km: float

@app.on_event("startup")
def startup():
    """Create database tables across all shards on startup"""
    init_shard_databases(Base.metadata)

@app.post("/trip/complete")
def complete_trip(request: TripCompletionRequest):
    """
    Calculates fare and archives trip into designated geographic database shard
    (e.g., Mumbai vs. Delhi) based on start_lat and start_lon payload coordinates.
    """
    BASE_FARE = 50
    PER_KM_RATE = 15
    total_fare = BASE_FARE + (request.distance_km * PER_KM_RATE)

    trip_id = f"trip_{uuid.uuid4().hex[:8]}"
    shard_key = resolve_shard_key(request.start_lat, request.start_lon)

    new_trip = Trip(
        trip_id=trip_id,
        rider_id=request.rider_id,
        driver_id=request.driver_id,
        start_lat=request.start_lat,
        start_lon=request.start_lon,
        end_lat=request.end_lat,
        end_lon=request.end_lon,
        distance_km=request.distance_km,
        fare_amount=round(total_fare, 2),
        status=TripStatus.COMPLETED
    )

    db = next(get_db_for_shard(shard_key))
    try:
        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)
        return {
            "status": "success",
            "trip_id": new_trip.trip_id,
            "fare_amount": new_trip.fare_amount,
            "shard_used": shard_key,
            "message": f"Trip billed successfully and stored in {shard_key.upper()} shard database."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction failed on shard '{shard_key}': {str(e)}")
