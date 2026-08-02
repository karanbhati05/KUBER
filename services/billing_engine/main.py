from fastapi import FastAPI , Depends , HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid
from models import Base , Trip , TripStatus
from database import get_db , engine

app = FastAPI(
    title= "KUBER Blling Engine",
    description="Handles fare calculation and permanent trip storage in MYSQL"
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
async def startup():
    "Create the database tables when the server starts"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/trip/complete")
async def complete_trip(request: TripCompletionRequest, db: AsyncSession = Depends(get_db)):
    "calculates the fare and permanently archives the trip"

    BASE_FARE = 50
    PER_KM_RATE = 15
    total_fare = BASE_FARE + (request.distance_km * PER_KM_RATE)

    trip_id = f"trip_{uuid.uuid4().hex[:8]}"

    new_trip = Trip(
        trip_id = trip_id,
        rider_id = request.rider_id,
        driver_id = request.driver_id,
        start_lat = request.start_lat,
        start_lon = request.start_lon,
        end_lat = request.end_lat,
        end_lon = request.end_lon,
        distance_km = request.distance_km,
        fare_amount = round(total_fare,2),
        status = TripStatus.COMPLETED
    )

    # ACID TRANSACTION
    try:
        db.add(new_trip)
        await db.commit()
        await db.refresh(new_trip)
        return{
            "status": "success",
            "trip_id": new_trip.trip_id,
            "fare_amount": new_trip.fare_amount,
            "message": "trip has been completed and billed successfully."
        }

    except Exception as e:
        await db.rollback()
        print(f"\n--- FATAL DB ERROR ---\n{str(e)}\n----------------------\n") 
        
        # 2. Return the exact error to the Swagger UI
        raise HTTPException(status_code=500, detail=f"Database transaction failed: {str(e)}")


    
