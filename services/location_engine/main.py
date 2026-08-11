from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import logging
import os
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KUBER Location Engine",
    description="Microservice for real-time driver tracking and proximity matching.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# In-Memory Drivers Storage Fallback if Redis is offline
in_memory_drivers = {
    "driver_101": {"lat": 19.0620, "lon": 72.8380, "driver_id": "driver_101"},
    "driver_102": {"lat": 19.0550, "lon": 72.8310, "driver_id": "driver_102"},
    "driver_103": {"lat": 19.0700, "lon": 72.8400, "driver_id": "driver_103"},
}

class DriverLocation(BaseModel):
    driver_id: str
    latitude: float
    longitude: float

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Redis connection check...")
    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.warning(f"Redis offline -> Operating in In-Memory fallback mode: {e}")

@app.post("/driver/location")
async def update_location(data: DriverLocation):
    in_memory_drivers[data.driver_id] = {
        "lat": data.latitude,
        "lon": data.longitude,
        "driver_id": data.driver_id
    }
    try:
        await redis_client.geoadd(
            name="active_drivers",
            values=(data.longitude, data.latitude, data.driver_id)
        )
    except Exception:
        pass

    return {
        "status": "success",
        "driver_id": data.driver_id
    }

@app.get("/rider/nearby")
async def find_nearby_drivers(
    latitude: float = Query(..., description="Rider's current latitude"),
    longitude: float = Query(..., description="Rider's current longitude"),
    radius_km: float = Query(5.0, description="Search radius in kilometers")
):
    try:
        nearby_drivers = await redis_client.geosearch(
            name="active_drivers",
            longitude=longitude,
            latitude=latitude,
            radius=radius_km,
            unit="km",
            withdist=True,
            sort="ASC"
        )
        if nearby_drivers:
            results = [
                {"driver_id": d[0], "distance_km": round(d[1], 2)}
                for d in nearby_drivers
            ]
            return {"drivers": results}
    except Exception:
        pass

    # Fallback to In-Memory Distance Math
    results = []
    for d_id, data in in_memory_drivers.items():
        d_lat = data["lat"]
        d_lon = data["lon"]
        # Haversine distance
        R = 6371
        d_lat_rad = math.radians(d_lat - latitude)
        d_lon_rad = math.radians(d_lon - longitude)
        a = math.sin(d_lat_rad / 2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(d_lat)) * math.sin(d_lon_rad / 2)**2
        dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        if dist <= radius_km:
            results.append({"driver_id": d_id, "distance_km": round(dist, 2)})

    results.sort(key=lambda x: x["distance_km"])
    return {"drivers": results}
