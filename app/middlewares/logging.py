import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"Method: {request.method} Path: {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {process_time:.4f}s"
        )
        
        return response
