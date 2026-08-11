import json
import random
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# Target URL for Billing Engine (Direct port 8003 or through API Gateway port 80)
BILLING_API_URL = "http://127.0.0.1:8003/trip/complete"

NUM_REQUESTS = 50       # Total synthetic trip requests to send
CONCURRENCY = 10        # Concurrent worker threads

# Coordinates Bounding Boxes for Synthetic Data Generation
MUMBAI_LAT_RANGE = (18.9000, 19.2500)
MUMBAI_LON_RANGE = (72.8000, 72.9800)

DELHI_LAT_RANGE = (28.4000, 28.8500)
DELHI_LON_RANGE = (76.8000, 77.3000)

def generate_synthetic_trip():
    """Generates realistic synthetic trip data in Mumbai or Delhi region."""
    # 75% Mumbai trips, 25% Delhi trips to test both database shards
    is_mumbai = random.random() < 0.75

    if is_mumbai:
        start_lat = round(random.uniform(*MUMBAI_LAT_RANGE), 4)
        start_lon = round(random.uniform(*MUMBAI_LON_RANGE), 4)
    else:
        start_lat = round(random.uniform(*DELHI_LAT_RANGE), 4)
        start_lon = round(random.uniform(*DELHI_LON_RANGE), 4)

    end_lat = round(start_lat + random.uniform(-0.04, 0.04), 4)
    end_lon = round(start_lon + random.uniform(-0.04, 0.04), 4)
    distance_km = round(random.uniform(1.5, 28.0), 2)

    return {
        "rider_id": f"rider_{random.randint(1000, 9999)}",
        "driver_id": f"driver_{random.randint(100, 999)}",
        "start_lat": start_lat,
        "start_lon": start_lon,
        "end_lat": end_lat,
        "end_lon": end_lon,
        "distance_km": distance_km
    }

def send_trip_request(request_id: int):
    """Sends a single HTTP POST request to the Billing Engine."""
    payload = generate_synthetic_trip()
    data = json.dumps(payload).encode('utf-8')

    req = urllib.request.Request(
        BILLING_API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            resp_body = json.loads(response.read().decode('utf-8'))
            return {
                "success": True,
                "request_id": request_id,
                "status_code": response.status,
                "latency_ms": latency_ms,
                "trip_id": resp_body.get("trip_id"),
                "fare_amount": resp_body.get("fare_amount"),
                "shard_used": resp_body.get("shard_used", "N/A"),
                "rider_id": payload["rider_id"]
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "request_id": request_id,
            "status_code": e.code,
            "latency_ms": latency_ms,
            "error": str(e)
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "request_id": request_id,
            "status_code": 500,
            "latency_ms": latency_ms,
            "error": str(e)
        }

def run_stress_test():
    print("==========================================================================")
    print("      KUBER BILLING ENGINE CONCURRENCY & SHARDING STRESS TEST             ")
    print("==========================================================================")
    print(f" Target API Endpoint : {BILLING_API_URL}")
    print(f" Total Requests      : {NUM_REQUESTS}")
    print(f" Worker Threads      : {CONCURRENCY}")
    print("--------------------------------------------------------------------------\n")

    start_total_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_trip_request, i + 1) for i in range(NUM_REQUESTS)]

        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            if res["success"]:
                print(
                    f" [REQ #{res['request_id']:02d}] SUCCESS ({res['latency_ms']} ms) | "
                    f"Rider: {res['rider_id']} | Trip: {res['trip_id']} | "
                    f"Fare: Rs.{res['fare_amount']} | Shard: {res['shard_used'].upper()}"
                )
            else:
                print(
                    f" [REQ #{res['request_id']:02d}] FAILED ({res['latency_ms']} ms) | "
                    f"Error: {res['error']}"
                )

    total_time = round(time.time() - start_total_time, 2)
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    avg_latency = round(sum(r["latency_ms"] for r in results) / len(results), 2) if results else 0
    throughput = round(len(results) / total_time, 2) if total_time > 0 else 0

    mumbai_count = sum(1 for r in successful if r.get("shard_used") == "mumbai")
    delhi_count = sum(1 for r in successful if r.get("shard_used") == "delhi")

    print("\n==========================================================================")
    print("                      STRESS TEST METRICS SUMMARY                         ")
    print("==========================================================================")
    print(f" Total Executed Requests : {len(results)}")
    print(f" Successful Transactions : {len(successful)} ({round(len(successful)/len(results)*100, 1)}%)")
    print(f" Failed Transactions     : {len(failed)}")
    print(f" Total Execution Time    : {total_time} s")
    print(f" Average Latency         : {avg_latency} ms")
    print(f" System Throughput       : {throughput} req/sec")
    print("--------------------------------------------------------------------------")
    print(" Database Shard Distribution:")
    print(f"   - MUMBAI SHARD        : {mumbai_count} trips written")
    print(f"   - DELHI SHARD         : {delhi_count} trips written")
    print("==========================================================================\n")

if __name__ == "__main__":
    run_stress_test()
