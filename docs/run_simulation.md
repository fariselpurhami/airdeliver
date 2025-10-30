# Running the airdeliver Drone Simulation Locally

This guide explains how to run the full drone simulation stack using Docker Compose.

## Prerequisites

1.  **Docker & Docker Compose:** Ensure you have recent versions installed.
2.  **Repository:** Clone the `airdeliver` monorepo.
3.  **Environment Variables:**
    * Create a `.env` file in the `drone_client` directory with at least:
        ```env
        DRONE_ID=SIM-001
        WEBSOCKET_URI=ws://api:8000/ws/drones/
        MAVLINK_CONNECTION=udp://px4-sitl:14540
        AUTH_TOKEN=your_secure_token_sim # Must match DRONE_JWT_SECRET in api's config
        ```
    * Ensure the main `.env` file for `apps/api` has necessary settings, including `DRONE_JWT_SECRET`.

## Running the Simulation

1.  **Open Terminal:** Navigate to the root directory of the `airdeliver` monorepo.

2.  **Build and Start All Services:** Use both compose files to bring up the core backend, the database, the web frontend, the PX4 SITL simulator, and the drone companion software.
    ```bash
    docker compose -f docker-compose.yml -f docker-compose.drone.yml up --build -d
    ```
    * `--build`: Ensures images are built with the latest code.
    * `-d`: Runs containers in detached mode (background).

3.  **Check Container Status:** Verify all containers are running and healthy.
    ```bash
    docker compose -f docker-compose.yml -f docker-compose.drone.yml ps
    ```
    You should see `airdeliver-db`, `airdeliver-api`, `airdeliver-web`, `airdeliver-px4-sitl`, and `airdeliver-companion-sim` listed, ideally with a `healthy` or `running` status (after the initial startup period).

4.  **Monitor Logs (Optional):** View logs for specific services:
    * API Server (including WebSockets): `docker compose logs -f api`
    * Companion Software: `docker compose logs -f companion`
    * PX4 SITL: `docker compose logs -f px4-sitl`

## Interacting with the Simulation

1.  **Web Interface:** Access the main web UI at `http://localhost:3000`.
2.  **Sending Commands:** Use the internal API endpoint to send commands to the simulated drone (e.g., `SIM-001`). Example using `curl`:
    ```bash
    curl -X POST http://localhost:8000/ws/internal/send_command/SIM-001 \
    -H "Content-Type: application/json" \
    -d '{
      "type": "command",
      "command_id": "cmd-sim-test-01",
      "timestamp": "2025-10-28T14:00:00Z",
      "payload": {
        "action": "start_mission",
        "mission": {
          "mission_id": "m-sim-test-01",
          "waypoints": [
            {"lat": 34.0530, "lon": -118.2440, "alt_m": 10.0},
            {"lat": 34.0535, "lon": -118.2445, "alt_m": 10.0}
          ]
        },
        "requires_ack": true
      }
    }'
    ```
3.  **Viewing Telemetry:** Check the drone tracking page in the web UI (e.g., `http://localhost:3000/tracking/<orderId>`) or monitor the WebSocket connection using a debugging tool if needed. Telemetry data is also persisted via the API.
4.  **QGroundControl (Optional):** Connect QGroundControl to the SITL instance for visualization by adding a UDP Comm Link to `localhost:14550` (if you mapped port 14550 in `docker-compose.drone.yml`).

## Stopping the Simulation

```bash
docker compose -f docker-compose.yml -f docker-compose.drone.yml down
