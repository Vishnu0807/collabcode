# CollabCode
A production-ready real-time collaborative code editor allowing multiple users to edit the same file simultaneously without conflicts. Built with a robust CRDT algorithm and a highly scalable backend architecture.

## Architecture

```text
       Browser 1          Browser 2
          |                  |
    +-----v------------------v-----+
    |        React Frontend        |
    +--------------+---------------+
                   | (WebSockets & REST)
    +--------------v---------------+
    |      FastAPI Backend         |<---> [ Prometheus / Grafana ]
    +------+---------------+-------+
           |               |
    +------v------+ +------v------+
    | PostgreSQL  | |   Redis     |
    | (Persistence) | (Pub/Sub)   |
    +-------------+ +-------------+
```

## Tech Stack
| Layer | Technology |
|---|---|
| Frontend | React, Vite, Monaco Editor |
| Backend | Python, FastAPI, Uvicorn |
| Database | PostgreSQL, Async SQLAlchemy |
| Real-Time | WebSockets, Redis |
| Infrastructure | Docker, Kubernetes |
| Monitoring | Prometheus, Grafana |

## Local Setup
1. Clone the repository.
2. Run `docker-compose up --build -d` inside the root directory.
3. Open `http://localhost:3000` in your browser.

## How CRDT Works Here
Our CRDT (Conflict-free Replicated Data Type) ensures that even if two users type at the exact same moment, the document always reaches the exact same state locally on all machines. Each character gets a unique, immutable ID formatting like `userClockId_1`. If two characters clash at the same insertion index, we sort their IDs lexicographically; the "larger" ID skips past the "smaller" ID. This guarantees deterministic ordering network-wide without a central locking server.

## WebSocket Flow
1. **User types**: A character is inserted into the local browser CRDT representation.
2. **Socket transmit**: The change event (`{"type": "insert", "char": "a", "id": "user1_42", "after_id": "user1_41"}`) travels via WebSocket to the FastAPI backend.
3. **Backend injects**: FastAPI applies this logic into its server-side in-memory map.
4. **Redis broadcast**: FastAPI publishes the payload to the channel `room:<id>`, triggering all other FastAPI instances to hear the event.
5. **Clients update**: All other WebSocket clients in the room receive the payload, apply it to their local model, and update their Monaco Editor view instantly.

## Kubernetes Deployment
All manifests are available in the `k8s/` folder and configured for horizontal autoscaling constraints.
```sh
kubectl apply -f k8s/
```
The application will be exposed via the NGINX ingress routing `/api/*` to the backend cluster and `/*` to the static frontend bundle.

## Monitoring
The FastApi system dynamically exposes latency, message counts, and active connections at `/metrics`. 
- Open Grafana at `http://localhost:3001` (if running locally via docker-compose)
- Access the pre-configured "CollabCode Real-time Metrics" dashboard.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Please ensure tests are updated as appropriate.

## License
MIT
