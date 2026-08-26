from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.auth import router as auth_router, verify_token
from routers import courses, emails, customers, integrations
from db import engine
from logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.connect():
            logger.info("Database pool connection established successfully.")
        
    except Exception as e:
        logger.warning(f"Warning: Database warm-up failed: {e}")
        
    yield
    
    engine.dispose()
    logger.info("Database engine disposed.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

protected = [Depends(verify_token)]

app.include_router(courses.router, dependencies=protected)
app.include_router(emails.router, dependencies=protected)
app.include_router(customers.router, dependencies=protected)
app.include_router(integrations.router, dependencies=protected)