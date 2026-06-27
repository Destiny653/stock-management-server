from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from db.mongodb import init_db

from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from gridfs.errors import NoFile
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from api.v1.router import api_router
from api.v1.swagger_auth import get_swagger_auth
from middlewares.logging import LoggingMiddleware
from core.uploads import UPLOAD_ROOT, get_upload_dir
from db.mongodb import db

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

# GridFS route for serving uploads
@app.get("/uploads/{bucket_name}/{filename}")
async def get_gridfs_file(bucket_name: str, filename: str):
    from db.mongodb import db
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    fs = AsyncIOMotorGridFSBucket(db, bucket_name=bucket_name)
    try:
        # Find the file by filename
        cursor = fs.find({"filename": filename})
        file_docs = await cursor.to_list(length=1)
        if not file_docs:
            raise HTTPException(status_code=404, detail="Not Found")
        
        grid_out = await fs.open_download_stream_by_name(filename)
        
        async def file_streamer():
            while chunk := await grid_out.readchunk():
                yield chunk
                
        content_type = grid_out.metadata.get("contentType", "application/octet-stream") if grid_out.metadata else "application/octet-stream"
        
        return StreamingResponse(file_streamer(), media_type=content_type)
    except NoFile:
        raise HTTPException(status_code=404, detail="Not Found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_db_client():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to StockFlow API"}
