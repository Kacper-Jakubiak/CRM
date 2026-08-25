from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router, verify_token
from routers import courses, emails, customers, integrations

app = FastAPI()

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