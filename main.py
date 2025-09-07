import logging
from contextlib import asynccontextmanager

from app.api import routes as api_routes
from app.api.schemas import ApiResponse
from app.config import scraper_config
from app.scheduler import schedule_jobs
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logging.basicConfig(
    level=scraper_config.LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)

scheduler = AsyncIOScheduler(timezone=scraper_config.TIMEZONE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the scheduler's lifecycle with the FastAPI application.
    """
    logging.info(f"Scheduler starting in timezone {scraper_config.TIMEZONE}.")
    schedule_jobs(scheduler)
    scheduler.start()
    yield
    logging.info("Scheduler shutting down.")
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch all unhandled exceptions and return a
    standardized JSON error response.
    """
    status_code = 500
    message = "An internal server error occurred"
    if isinstance(exc, StarletteHTTPException):
        status_code = exc.status_code
        message = str(exc.detail)

    return JSONResponse(
        status_code=status_code,
        content=ApiResponse(
            status="error",
            message=message,
            data=None,
        ).model_dump(exclude_none=True),
    )


app.include_router(api_routes.router)
