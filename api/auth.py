import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from logger import logger

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("CRITICAL: JWT_SECRET environment variable is not set!")

ADMIN_USER = os.getenv("ADMIN_USER", "")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "")
if not ADMIN_USER or not ADMIN_PASS:
    raise ValueError("CRITICAL: ADMIN_USER or ADMIN_PASS environment variable is not set!")
ALGORITHM = "HS256"

router = APIRouter(prefix="/api", tags=["Auth"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginRequest):
    logger.info(f"Login attempt initiated for user: {data.username}, password: {data.password}")
    # print(f"DEBUG INPUT -> User: '{data.username}', Pass: '{data.password}'")
    # print(f"DEBUG ENV   -> Admin: '{ADMIN_USER}', Pass: '{ADMIN_PASS}'")

    is_user_correct = secrets.compare_digest(data.username, ADMIN_USER)
    is_pass_correct = secrets.compare_digest(data.password, ADMIN_PASS)

    if not (is_user_correct and is_pass_correct):
        logger.warning(f"Failed login attempt for user: {data.username} - Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    payload = {
        "sub": data.username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

    logger.info(f"Successful login for user: {data.username}. Token issued.")
    return {"access_token": token}

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validates the JWT bearer token sent in HTTP headers."""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )