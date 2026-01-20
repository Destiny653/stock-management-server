from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from db.mongodb import init_db

from fastapi.staticfiles import StaticFiles
from api.v1.router import api_router
from middlewares.logging import LoggingMiddleware
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(LoggingMiddleware)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
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
