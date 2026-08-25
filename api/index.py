import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import courses, emails, customers, integrations

app = FastAPI()
security = HTTPBearer()

load_dotenv()
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "")

def verify_admin(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verifies that the provided token matches your ADMIN_SECRET_KEY."""
    token = credentials.credentials
    if not secrets.compare_digest(token, ADMIN_SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    return True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(verify_admin)]

app.include_router(courses.router, dependencies=protected)
app.include_router(emails.router, dependencies=protected)
app.include_router(customers.router, dependencies=protected)
app.include_router(integrations.router, dependencies=protected)