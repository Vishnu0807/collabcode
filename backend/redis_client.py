# redis_client.py
# Establishes an async connection to the central Redis pub/sub broker.
# Allows WebSocket rooms to broadcast events globally to other application instances.

import os
import json
import aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Creates an async connection pool to the Redis server configuration.
def get_redis_connection():
    return aioredis.from_url(REDIS_URL, decode_responses=True)

# Publishes an event dictionary payload as a JSON string to a specific channel.
async def publish(channel: str, message: dict):
    client = get_redis_connection()
    await client.publish(channel, json.dumps(message))
    await client.close()

# Subscribes to a specific Redis channel to read live incoming messages.
async def subscribe(channel: str):
    client = get_redis_connection()
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub
