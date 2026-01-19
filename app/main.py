from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongodb import init_db

from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.middlewares.logging import LoggingMiddleware
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(LoggingMiddleware)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (uploads)
os.makedirs("uploads/products", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_db_client():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to StockFlow API"}
