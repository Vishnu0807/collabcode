from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import asyncio
import json

from redis_client import publish, subscribe
from auth import hash_password, verify_password, create_access_token, get_current_user

app = FastAPI(title="CollabCode API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],    
)

# ---------------------------------------------------------
# AUTHENTICATION DATA & ROUTES
# ---------------------------------------------------------
# Temporary in-memory database mapping usernames to hashed passwords
fake_users_db: Dict[str, str] = {}

# Pydantic schema enforcing incoming JSON structures
class UserCredentials(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(user: UserCredentials):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    # Never store raw passwords; hash them immediately
    fake_users_db[user.username] = hash_password(user.password)
    
    # Optionally, we can dynamically log them in right after registering
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login")
# OAuth2PasswordRequestForm allows FastAPI's interactive Swagger UI "Authorize" button to work smoothly
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Look up the user in database
    hashed_password = fake_users_db.get(form_data.username)
    
    # 2. Verify existence and correctness of password
    if not hashed_password or not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Create the JWT payload (traditionally 'sub' stands for subject/username)
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
# Adding Depends(get_current_user) throws an automatic 401 error if there's no valid token!
def get_my_profile(current_user: dict = Depends(get_current_user)):
    username = current_user.get("sub")
    return {"message": f"Welcome back, {username}! This is top-secret protected data.", "user_details": current_user}

# ---------------------------------------------------------
# WEBSOCKET & REDIS COLLABORATION ROUTES
# ---------------------------------------------------------

rooms: Dict[str, Dict[str, WebSocket]] = {}

@app.get("/")
def read_root():
    return {"message": "Welcome to the CollabCode API. The server is up and running!"}

async def broadcast_to_room(room_id: str, message: dict, exclude_user: str = None):
    if room_id in rooms:
        for active_user_id, connection in rooms[room_id].items():
            if active_user_id != exclude_user:
                await connection.send_json(message)

async def redis_listener(room_id: str):
    channel = f"room:{room_id}"
    pubsub = await subscribe(channel)
    
    async for message in pubsub.listen():
        if room_id not in rooms:
            break
            
        if message['type'] == 'message':
            data = json.loads(message['data'])
            await broadcast_to_room(room_id, data, exclude_user=data.get("user_id"))

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = {}
        asyncio.create_task(redis_listener(room_id))
        
    rooms[room_id][user_id] = websocket
    await publish(f"room:{room_id}", {"type": "user_joined", "user_id": user_id})
    
    try:
        while True:
            data = await websocket.receive_json()
            data["user_id"] = user_id
            await publish(f"room:{room_id}", data)
            
    except WebSocketDisconnect:
        if room_id in rooms and user_id in rooms[room_id]:
            del rooms[room_id][user_id]
            if not rooms[room_id]:
                del rooms[room_id]
        await publish(f"room:{room_id}", {"type": "user_left", "user_id": user_id})
