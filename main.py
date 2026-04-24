from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from db.mongodb import init_db

from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from api.v1.router import api_router
from api.v1.swagger_auth import get_swagger_auth
from middlewares.logging import LoggingMiddleware
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
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

# Protected Documentation Routes
@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(current_active_user=Depends(get_swagger_auth)):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)

@app.get("/docs", include_in_schema=False)
async def get_documentation(current_active_user=Depends(get_swagger_auth)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Project Documentation")

@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(current_active_user=Depends(get_swagger_auth)):
    return get_redoc_html(openapi_url="/openapi.json", title="Project Documentation")

# Static files (uploads)
os.makedirs("uploads/products", exist_ok=True)
os.makedirs("uploads/storefront", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_db_client():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to StockFlow API"}
