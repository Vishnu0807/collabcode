import json
import aioredis

# 1. Create a connection function
# Establish an async connection to the local Redis server.
def get_redis_connection():
    # Note: aioredis.from_url creates a client immediately, so it doesn't require 'await'.
    # Enabling decode_responses=True converts raw bytes into readable Python strings automatically.
    return aioredis.from_url("redis://localhost:6379", decode_responses=True)

# 2. Publish function
# Broadcasts a JSON message to a specified channel so anyone listening will receive it.
async def publish(channel: str, message: dict):
    client = get_redis_connection()
    
    # Since Redis transports simple text/bytes, we convert our Python dictionary into a JSON string.
    message_string = json.dumps(message)
    
    # Push the message to the requested channel
    await client.publish(channel, message_string)
    
    # Responsibly close our short-lived connection
    await client.close()

# 3. Subscribe function
# Subscribes to a channel and returns a 'pubsub' object that can listen for incoming data.
async def subscribe(channel: str):
    client = get_redis_connection()
    
    # Ask Redis for a dedicated Pub/Sub object designed strictly for listening
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    
    # We return this pubsub object so the calling code can loop over it forever to get messages
    return pubsub
