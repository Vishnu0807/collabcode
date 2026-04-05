from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

app = FastAPI(title="CollabCode API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],    
)

# Store active connections: room_id -> {user_id: websocket object}
# Example: {"room_1": {"userA": <WebSocket>, "userB": <WebSocket>}}
rooms: Dict[str, Dict[str, WebSocket]] = {}

@app.get("/")
def read_root():
    return {"message": "Welcome to the CollabCode API. The server is up and running!"}

# Helper function to send a JSON message to everyone in a room except one user
async def broadcast_to_room(room_id: str, message: dict, exclude_user: str = None):
    if room_id in rooms:
        for active_user_id, connection in rooms[room_id].items():
            if active_user_id != exclude_user:
                await connection.send_json(message)

# The main WebSocket endpoint handling real-time collaboration
@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    # Accept the incoming connection request
    await websocket.accept()
    
    # Create the room if it doesn't exist yet
    if room_id not in rooms:
        rooms[room_id] = {}
        
    # Store the user's connection so we can send messages to them later
    rooms[room_id][user_id] = websocket
    
    # Tell everyone else in this room that a new user has joined
    await broadcast_to_room(room_id, {"type": "user_joined", "user_id": user_id}, exclude_user=user_id)
    
    try:
        # Keep listening for messages from this user forever
        while True:
            # Wait until the user sends a JSON message
            data = await websocket.receive_json()
            
            # Instantly forward (broadcast) this message to everyone else in the room
            await broadcast_to_room(room_id, data, exclude_user=user_id)
            
    except WebSocketDisconnect:
        # This block triggers automatically when the user closes the tab or drops connection
        if room_id in rooms and user_id in rooms[room_id]:
            del rooms[room_id][user_id]
            
            # Optional cleanup: remove the room entirely if nobody is left
            if not rooms[room_id]:
                del rooms[room_id]
                
        # Tell everyone else that this user has disconnected
        await broadcast_to_room(room_id, {"type": "user_left", "user_id": user_id})
