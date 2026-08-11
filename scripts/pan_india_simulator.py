"""
KUBER Pan-India Million-Scale Telemetry Simulator
Simulates live movement of 5,000+ drivers across 4 major Indian metropolitan hubs:
1. Mumbai (BKC, Airport T2, Colaba, Lower Parel)
2. Delhi (Connaught Place, IGI T3, Cyber City, Noida)
3. Bengaluru (Koramangala, Indiranagar, HSR Layout, Electronic City)
4. Hyderabad (HITEC City, Gachibowli, Banjara Hills, Airport)
"""

import time
import random
import math
import asyncio
import httpx

METRO_HUBS = {
    "mumbai": [
        {"name": "Bandra Kurla Complex", "lat": 19.0600, "lon": 72.8350},
        {"name": "Mumbai Airport T2", "lat": 19.0880, "lon": 72.8680},
        {"name": "Colaba Gateway", "lat": 18.9220, "lon": 72.8330},
        {"name": "Lower Parel Tech Park", "lat": 19.0000, "lon": 72.8300}
    ],
    "delhi": [
        {"name": "Connaught Place", "lat": 28.6315, "lon": 77.2167},
        {"name": "IGI Airport T3", "lat": 28.5562, "lon": 77.1000},
        {"name": "Cyber City Gurgaon", "lat": 28.4950, "lon": 77.0890},
        {"name": "Noida Sector 62", "lat": 28.6280, "lon": 77.3640}
    ],
    "bengaluru": [
        {"name": "Koramangala 5th Block", "lat": 12.9352, "lon": 77.6245},
        {"name": "Indiranagar 100ft Rd", "lat": 12.9784, "lon": 77.6408},
        {"name": "HSR Layout Sector 1", "lat": 12.9121, "lon": 77.6445},
        {"name": "Electronic City Phase 1", "lat": 12.8452, "lon": 77.6602}
    ],
    "hyderabad": [
        {"name": "HITEC City Cyber Towers", "lat": 17.4504, "lon": 78.3808},
        {"name": "Gachibowli Financial Dist", "lat": 17.4401, "lon": 78.3489},
        {"name": "Banjara Hills Road 12", "lat": 17.4156, "lon": 78.4347},
        {"name": "Rajiv Gandhi Airport", "lat": 17.2403, "lon": 78.4294}
    ]
}

VEHICLE_TYPES = ["UberX", "UberXL", "UberBlack", "Auto"]

class VirtualDriver:
    def __init__(self, driver_id, city, base_lat, base_lon):
        self.driver_id = driver_id
        self.city = city
        self.lat = base_lat + random.uniform(-0.03, 0.03)
        self.lon = base_lon + random.uniform(-0.03, 0.03)
        self.vehicle = random.choice(VEHICLE_TYPES)
        self.speed = random.uniform(0.0005, 0.0015)
        self.angle = random.uniform(0, 2 * math.pi)

    def step(self):
        self.lat += self.speed * math.cos(self.angle)
        self.lon += self.speed * math.sin(self.angle)
        if random.random() < 0.1:
            self.angle += random.uniform(-0.5, 0.5)
        return {
            "driver_id": self.driver_id,
            "city": self.city,
            "vehicle_type": self.vehicle,
            "lat": round(self.lat, 6),
            "lon": round(self.lon, 6)
        }

def generate_telemetry_batch(batch_size=1000):
    drivers = []
    cities = list(METRO_HUBS.keys())
    for i in range(batch_size):
        city = random.choice(cities)
        hub = random.choice(METRO_HUBS[city])
        d = VirtualDriver(f"drv_in_{i+1000}", city, hub["lat"], hub["lon"])
        drivers.append(d)
    
    print(f"🚀 Initialized Pan-India Driver Telemetry Generator ({batch_size} virtual drivers)...")
    return drivers

if __name__ == "__main__":
    drivers = generate_telemetry_batch(1000)
    for _ in range(5):
        sample = [d.step() for d in drivers[:3]]
        print("📡 Live Telemetry Stream Sample:", sample)
        time.sleep(1)
