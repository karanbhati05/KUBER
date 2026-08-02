from asyncio import wait
import asyncio
import json
import logging
import httpx
from aiokafka import AIOKafkaConsumer
import redis.asyncio as redis

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.from_url("redis://localhost:6379" , decode_responses = True)

async def process_ride_requests():

    consumer = AIOKafkaConsumer(
        'ride_requests',
        bootstrap_servers='localhost:9092',
        group_id = "dispatch_group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    await consumer.start()
    logger.info("Worker Started: Listeninh for ride requests")

    try:
        async for msg in consumer:
            request = msg.value
            rider_id = request['rider_id']
            logger.info(f"Processing request for rider {rider_id} at {request['pickup_lat']} {request['pickup_lon']}")

            async with httpx.AsyncClient() as client:
                try:
                    # calling the nearby_drivers endpoint on the other microservice
                    response = await client.get(
                        "http://localhost:8000/rider/nearby",
                        params = {
                            "latitude": request['pickup_lat'],
                            "longitude": request['pickup_lon'],
                            "radius_km": 5
                        }
                    )
                    data = response.json()
                except Exception as e:
                    logger.error(f"Error to contact Location Engine: {str(e)}")
                    continue
            
            drivers = data.get('drivers', [])
            if not drivers:
                logger.warning(f"No drivers found near {rider_id}")
                continue
            
            matched_driver = None
            for driver in drivers:
                driver_id = driver['driver_id']

                lock_acquired = await redis_client.set(f"lock:driver:{driver_id}"    , "locked" , nx = True , ex = 30)
                if lock_acquired:
                    matched_driver = driver
                    logger.info(f"SUCCESS: Locked {driver_id} for {rider_id} (Distance: {driver['distance_km']}km)")
                    break # exits loop after finding first available driver
                else:
                    logger.warning(f"Driver {driver_id} is currently on another ride")
            
            if not matched_driver:
                logger.error(f"All nearby drivers are currently busy for {rider_id}")
    finally:
        await consumer.stop()
        
if __name__ == "__main__":
    asyncio.run(process_ride_requests())
            
            
                        

            
