from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# 1. Configuration Constants
# Note: In production, the SECRET_KEY should be loaded from a secure environment variable!
SECRET_KEY = "collabcode_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 2. Setup Security Utilities
# Defines how we extract the token from headers and tells Swagger UI where to login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Defines bcrypt as our chosen password hashing algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AUTHENTICATION FUNCTIONS
# ---------------------------------------------------------

# Hashes a plain-text password for secure database storage
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Checks if a typed plain-text password matches the scrambled hash in the database
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Packs user data (like user_id) into a secure, signed JWT token string
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    
    # Add an expiration time to the token so it doesn't live forever
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Create the cryptographically signed token using our SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Reads a token, checks if it's still alive, and verifies it hasn't been tampered with
def verify_token(token: str):
    try:
        # If someone altered the token text, this will throw a JWTError
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ---------------------------------------------------------
# FASTAPI DEPENDENCY
# ---------------------------------------------------------

# This function acts as a guard. If you inject it into any route, the route instantly becomes protected!
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    
    # If the token is fake, expired, or tampered with, kick them out
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials - please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Valid token! Return the decoded data (like the user details) so the route can use it
    return payload
