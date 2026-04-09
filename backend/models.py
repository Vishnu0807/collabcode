# models.py
# This file contains all Pydantic models for request/response schemas.
# It defines data shapes for operations, cursors, and API payloads.

from pydantic import BaseModel
from typing import Optional

# Represents a single character inside the document, carrying a unique clock ID.
class CharObj(BaseModel):
    id: str  # Format: "user_clock" (e.g. "user1_42")
    char: str
    deleted: bool = False

# Represents an incoming editor action (inserting or deleting a character).
class EditOperation(BaseModel):
    type: str  # "insert" or "delete"
    char_obj: CharObj
    after_id: Optional[str] = None
    user_id: str
    room_id: str
    timestamp: float

# Information broadcast to show a user's cursor location and colour.
class UserCursor(BaseModel):
    user_id: str
    username: str
    color: str
    position: int

# Schema for incoming registration or login JSON requests.
class UserAuthRequest(BaseModel):
    username: str
    password: str

# Schema for incoming room creation requests.
class CreateRoomRequest(BaseModel):
    name: str

# Schema mapping what a room object should look like when sent to clients.
class RoomResponse(BaseModel):
    id: str
    name: str
