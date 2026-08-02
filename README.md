# KUBER 🚕 - Distributed Ride-Hailing Backend

A highly scalable, event-driven microservices architecture mimicking core ride-hailing backend systems (e.g., Uber, Lyft, Ola). Built to handle real-time geospatial querying, asynchronous event streaming, and concurrent financial transactions.

## 🏗️ System Architecture

The platform is decoupled into independent microservices communicating via HTTP, WebSockets, and message queues to ensure fault tolerance and horizontal scalability.

*   **Location Engine (Port 8000):** Ingests live telemetry from drivers. Utilizes Redis Geospatial indexing for high-performance, $O(\log N)$ proximity matching.
*   **Dispatch API & Worker (Port 8001 / Kafka):** Handles event-driven matchmaking. Pushes ride requests to an Apache Kafka topic to decouple heavy workload routing from the main API thread.
*   **WebSocket Hub (Port 8002):** Maintains persistent, bi-directional TCP connections with clients for live driver tracking and state synchronization.
*   **Billing Engine (Port 8003):** Manages fare calculation and enforces strict ACID properties via MySQL to guarantee financial data integrity and transaction rollbacks on failure.

## 💻 Tech Stack

*   **Language & Framework:** Python 3.10+, FastAPI, Uvicorn
*   **Databases & Caching:** MySQL 8.0, Redis
*   **Message Broker:** Apache Kafka
*   **ORM & Data Validation:** SQLAlchemy, Pydantic, aiomysql
*   **Infrastructure:** Docker, Docker Compose

## 🚀 Local Development Setup

### 1. Prerequisites
Ensure you have the following installed on your machine:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)
*   Python 3.10+
*   Git

### 2. Clone the Repository
```bash
git clone [https://github.com/karanbhati05/KUBER.git](https://github.com/karanbhati05/KUBER.git)
cd KUBER
'''

### 3. Spin Up Infrastructure

Start the Kafka broker, Redis cache, and MySQL database using Docker Compose.
*(Note: MySQL is mapped to port `3307` locally to prevent conflicts with local database installations).*

```bash
docker-compose up -d

```

### 4. Install Dependencies

Create a virtual environment and install the required Python packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```

### 5. Start the Microservices

Open 5 separate terminal windows and start the services concurrently:

**Terminal 1: Location Engine**

```bash
cd services/location_engine
uvicorn main:app --reload --port 8000

```

**Terminal 2: Dispatch API**

```bash
cd services/dispatch_engine
uvicorn main:app --reload --port 8001

```

**Terminal 3: Kafka Worker**

```bash
cd services/dispatch_engine
python worker.py

```

**Terminal 4: WebSocket Hub**

```bash
cd services/websocket_hub
uvicorn main:app --reload --port 8002

```

**Terminal 5: Billing Engine**

```bash
cd services/billing_engine
uvicorn main:app --reload --port 8003

```

## 🔌 API Documentation & Testing

FastAPI automatically generates interactive Swagger UI documentation for all microservices.

To test the **Billing Engine** and database integrity, navigate to:
👉 `http://127.0.0.1:8003/docs`

**Sample Payload for `POST /trip/complete`:**

```json
{
  "rider_id": "rider_karan_99",
  "driver_id": "driver_alpha_77",
  "start_lat": 19.0600,
  "start_lon": 72.8350,
  "end_lat": 19.0800,
  "end_lon": 72.8550,
  "distance_km": 4.5
}

```

## 🧠 Core Engineering Challenges Solved

* **The Double-Booking Problem:** Implemented Redis distributed locks to prevent race conditions where two riders might be assigned the same driver simultaneously.
* **Database Constraints & Migrations:** Configured precise SQLAlchemy models to maintain relational integrity without bottlenecking driver trip histories, correctly structuring unique index constraints.
* **Container Networking:** Engineered a robust `docker-compose.yml` to route local traffic, manage port conflicts, and maintain container state across reboots.
* **Swallowed Exceptions:** Architected strict database error handling in the API endpoints to log transaction rollbacks and expose `IntegrityError` violations for immediate debugging.

---

**Author:** Karan Bhati

**Contact:** [LinkedIn](https://www.linkedin.com/in/karanbhati) | [GitHub](https://github.com/karanbhati05)


```

```