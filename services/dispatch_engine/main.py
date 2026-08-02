from fastapi import HTTPException
from pydantic._internal._generate_schema import TUPLE_TYPES
from fastapi import FastAPI
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer
import json
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KUBER Dispatch Enigne",
    description="Handles ride requests and queues them via Apache Kafka to prevent bottlenecks and race conditions"
)

class RideRequest(BaseModel):
    rider_id: str
    latitude: float
    longitude: float

producer = None

@app.on_event("startup")
async def startup_event():
    """Initialize Kafka Producer"""
    global producer
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers = 'localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')

        )  
        await producer.start()  
        logger.info("Successfully connected to apache kafka")
    except Exception as e:
        logger.error(f"Failed to connect to Kafka: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanly close the kafka connection when shutting down"""
    if producer:
        await producer.stop()

@app.post("/ride/request")
async def request_ride(request: RideRequest):
    "accepts a ride req and instantly publishes it to kafka , this is O(1) operation prevents the API from blocking during high traffic"

    event_data = {
        "rider_id": request.rider_id,
        "pickup_lat": request.latitude,
        "pickup_lon": request.longitude,
        "status": "SEARCHING"
    }
    try:
        await producer.send_and_wait("ride_requests" , event_data)
        return{
            "status": "processing",
            "message": "Ride request recieved and queued for matching.",
            "event": event_data
        }
    except Exception as e:
        raise HTTPException(status_code = 500 , detail = f"Message Broker Error: {str(e)}")
    
        