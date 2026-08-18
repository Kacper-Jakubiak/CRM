from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import courses, emails, customers, integrations
from contextlib import asynccontextmanager
from db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs when app starts up, not during module imports
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(courses.router)
app.include_router(emails.router)
app.include_router(customers.router)
app.include_router(integrations.router)