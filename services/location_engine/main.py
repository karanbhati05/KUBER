from fastapi import FastAPI , HTTPException , Query
from pydantic import BaseModel
import redis.asyncio as redis
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title = "KUBER Location Engine" ,
    description = "Microservice for real-time driver tracking and proximity matching.",
    version="1.0.0"
)

redis_client = redis.from_url("redis://localhost:6379" , decode_responses = True)

class DriverLocation(BaseModel):
    driver_id: str
    latitude: float
    longitude: float

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Redis connection...")

    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")


@app.post("/driver/location")
async def update_location(data: DriverLocation):
    try:
        await redis_client.geoadd(
            name = "active_drivers",
            values = (data.longitude , data.latitude , data.driver_id)
        )

        return {
            "status": "success",
            "driver_id": data.driver_id
        }
    except Exception as e:
        raise HTTPException(status_code = 500 , detail = str(e))



@app.get("/rider/nearby")
async def find_nearby_drivers(
    latitude: float = Query(..., description="Rider's current latitude" ),
    longitude: float = Query(... , description="Rider's current longitude"),
    radius_km: float = Query(5.0 , description="Search radius in kilometers")
):
    #find all drivers within a specific radius
    try:
        nearby_drivers = await redis_client.geosearch(
            name = "active_drivers",
            longitude = longitude,
            latitude = latitude,
            radius = radius_km,
            unit = "km",
            withdist = True,
            sort = "ASC"
        )
        
        if not nearby_drivers:
            return{"drivers": [] , "message": "No drivers available nearby."}
        
        results = [
            {
                "driver_id": driver[0],
                "distance_km": round(driver[1],2)
            }
            for driver in nearby_drivers
        ]

        return{"drivers": results}

    except Exception as e:
        raise HTTPException(status_code = 500 , detail = str(e))


