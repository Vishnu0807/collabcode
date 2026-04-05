from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import json
from redis_client import publish, subscribe

app = FastAPI(title="CollabCode API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],    
)

# Active local connections: room_id -> {user_id: websocket object}
rooms: Dict[str, Dict[str, WebSocket]] = {}

@app.get("/")
def read_root():
    return {"message": "Welcome to the CollabCode API. The server is up and running!"}

# Helper: sends a JSON message to everyone stored locally in a room
async def broadcast_to_room(room_id: str, message: dict, exclude_user: str = None):
    if room_id in rooms:
        for active_user_id, connection in rooms[room_id].items():
            if active_user_id != exclude_user:
                await connection.send_json(message)

# Background Task: Constantly listens to Redis for a specific room
async def redis_listener(room_id: str):
    channel = f"room:{room_id}"
    pubsub = await subscribe(channel)
    
    # This loop runs forever, instantly catching messages pushed to this Redis channel
    async for message in pubsub.listen():
        # Clean up the task if everyone has left the room
        if room_id not in rooms:
            break
            
        # We only care about data messages (type "message")
        if message['type'] == 'message':
            data = json.loads(message['data'])
            # When Redis gives us a message, we broadcast it to our LOCAL web sockets!
            # We exclude the original sender so they don't receive their own keystroke.
            await broadcast_to_room(room_id, data, exclude_user=data.get("user_id"))

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = {}
        # If this is a brand new room, spawn a background task to listen to Redis for it!
        asyncio.create_task(redis_listener(room_id))
        
    rooms[room_id][user_id] = websocket
    
    # Instead of broadcasting locally, we PUBLISH to Redis so ALL servers see the join
    await publish(f"room:{room_id}", {"type": "user_joined", "user_id": user_id})
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Embed the user_id into the payload so receivers know who sent it
            data["user_id"] = user_id
            
            # Step 1: Forward the user's keystroke straight to Redis
            await publish(f"room:{room_id}", data)
            
    except WebSocketDisconnect:
        if room_id in rooms and user_id in rooms[room_id]:
            del rooms[room_id][user_id]
            if not rooms[room_id]:
                del rooms[room_id]
                
        # Send a global quit message through Redis
        await publish(f"room:{room_id}", {"type": "user_left", "user_id": user_id})
