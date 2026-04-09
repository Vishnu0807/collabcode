# main.py
# The primary FastAPI entrypoint, combining web sockets, REST routes, and dependencies.
# Handles all HTTP endpoints, CRDT broadcasting, and exports Prometheus server metrics.

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import asyncio
import json
from prometheus_client import Gauge, Counter, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.responses import Response

from redis_client import publish, subscribe
from auth import create_access_token, get_current_user, hash_password, verify_password
from models import UserAuthRequest, CreateRoomRequest, RoomResponse
from database import init_db, get_db, User, Room, get_recent_snapshots, snapshot_background_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import crdt

app = FastAPI(title="CollabCode API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Prometheus Metrics
active_connections = Gauge('active_connections', 'Current active websocket connections')
messages_total = Counter('messages_total', 'Total WebSocket messages')
message_latency = Histogram('message_latency_seconds', 'Message handling latency')

# Memory store for active connections and fast document state
active_rooms: Dict[str, Dict[str, WebSocket]] = {}
room_documents: Dict[str, List[dict]] = {}

# Executed immediately upon application startup to scaffold required data tables.
@app.on_event("startup")
async def startup_event():
    await init_db()

# Exposes Prometheus metrics output for the monitoring stack scraper to collect.
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Re-registers a new user and safely deposits a bcrypt version of their password in DB.
@app.post("/register")
async def register(user: UserAuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalars().first(): raise HTTPException(400, "Username exists")
    db_user = User(username=user.username, hashed_password=hash_password(user.password))
    db.add(db_user)
    await db.commit()
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}

# Validates user login attempt and grants a fresh JWT for continued secure API usage.
@app.post("/login")
async def login(user: UserAuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalars().first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}

# Creates a new editing session room yielding a unique ID.
@app.post("/rooms")
async def create_room(req: CreateRoomRequest, db: AsyncSession = Depends(get_db)):
    import uuid
    room_id = str(uuid.uuid4())
    db_room = Room(id=room_id, name=req.name)
    db.add(db_room)
    await db.commit()
    return {"id": room_id, "name": req.name}

# Retrieves all historical snapshot copies saved via our periodic background task.
@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, db: AsyncSession = Depends(get_db)):
    snapshots = await get_recent_snapshots(db, room_id)
    return [{"id": s.id, "saved_at": s.saved_at, "document_json": s.document_json} for s in snapshots]

# Provides room basic details and boots the async CRDT persistence script if needed.
@app.get("/rooms/{room_id}")
async def get_room(room_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalars().first()
    if not room: raise HTTPException(404, "Room not found")
    if room_id not in room_documents:
        room_documents[room_id] = []
        asyncio.create_task(snapshot_background_task(room_id, lambda r: room_documents.get(r)))
    return {"id": room.id, "name": room.name, "content": room_documents[room_id]}

# Scans Redis pub-sub for updates, broadcasting edits cleanly down to Websocket clients.
async def redis_listener(room_id: str):
    pubsub = await subscribe(f"room:{room_id}")
    async for msg in pubsub.listen():
        if room_id not in active_rooms: break
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            for uid, connection in active_rooms[room_id].items():
                if uid != data.get("user_id"): await connection.send_json(data)

# Accepts WebSocket traffic, binds connection to room state, and pipes events properly.
@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    if room_id not in active_rooms:
        active_rooms[room_id] = {}
        if room_id not in room_documents: room_documents[room_id] = []
        asyncio.create_task(redis_listener(room_id))
    
    active_rooms[room_id][user_id] = websocket
    active_connections.inc()
    await publish(f"room:{room_id}", {"type": "user_joined", "user_id": user_id})
    try:
        while True:
            with message_latency.time():
                data = await websocket.receive_json()
                messages_total.inc()
                data["user_id"] = user_id
                
                if data.get("type") in ["insert", "delete"]:
                    char_obj = data["char_obj"]
                    if data["type"] == "insert": crdt.insert(room_documents[room_id], char_obj, data.get("after_id"))
                    elif data["type"] == "delete": crdt.delete(room_documents[room_id], char_obj["id"])
                    
                await publish(f"room:{room_id}", data)
    except WebSocketDisconnect:
        del active_rooms[room_id][user_id]
        if not active_rooms[room_id]: del active_rooms[room_id]
        active_connections.dec()
        await publish(f"room:{room_id}", {"type": "user_left", "user_id": user_id})

# Provides a simple healthcheck route confirming application layout.
@app.get("/")
def read_root(): return {"status": "ok"}
