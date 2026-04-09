# database.py
# Manages connection to PostgreSQL via async SQLAlchemy and sets up our ORM schemas.
# Also handles background saving tasks to ensure our documents are backed up.

import os
import json
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.future import select

# Grab the database URL from the environment or fallback to localhost for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/collabcode"
)

# Initialize the async SQLAlchemy engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory for producing standard async database sessions
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base model to build SQLAlchemy table maps from
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), index=True, nullable=False)
    document_json = Column(Text, nullable=False)
    saved_at = Column(DateTime(timezone=True), server_default=func.now())

# Creates all the tables defined above if they do not already exist in Postgres.
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Periodically saves the in-memory document state into the database as a JSON snapshot.
async def snapshot_background_task(room_id: str, get_document_func):
    while True:
        await asyncio.sleep(30)
        current_document = get_document_func(room_id)
        if current_document is not None:
            async with AsyncSessionLocal() as session:
                doc_json = json.dumps(current_document)
                snapshot = DocumentSnapshot(room_id=room_id, document_json=doc_json)
                session.add(snapshot)
                await session.commit()

# Fetches the single most recent document snapshot for a room from the database.
async def get_latest_snapshot(session: AsyncSession, room_id: str):
    query = select(DocumentSnapshot).filter(DocumentSnapshot.room_id == room_id)
    query = query.order_by(DocumentSnapshot.saved_at.desc()).limit(1)
    result = await session.execute(query)
    return result.scalars().first()

# Fetches the 50 most recent snapshots for history tracking, ordered chronologically.
async def get_recent_snapshots(session: AsyncSession, room_id: str):
    query = select(DocumentSnapshot).filter(DocumentSnapshot.room_id == room_id)
    query = query.order_by(DocumentSnapshot.saved_at.desc()).limit(50)
    result = await session.execute(query)
    snapshots = result.scalars().all()
    return snapshots[::-1]

# Injects database sessions into our FastAPI endpoints securely.
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
