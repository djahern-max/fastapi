from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from app.routers import (
    register,
    login,
    video_upload,
    display_videos,
    projects,
    comments,
    conversations,
    profile,
    agreements,
    public_profile,
    request as requests_router,
    feedback,
    payment,
    vote,
    ratings,
    snagged_requests,
    marketplace,
)
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import sys


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.endswith((".ico", ".png", ".svg", ".json")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Load environment variables first
load_dotenv()

# Configure logging based on environment
if os.getenv("ENV") == "production":
    LOG_DIR = "/var/log/ryzeapi"
else:
    # Use a local directory for development
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# Create the log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
    ],
)
logger = logging.getLogger(__name__)


# Add startup logging
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RYZE.AI API")
    logger.info(f"Environment: {os.getenv('ENV')}")
    logger.info(f"Allowed origins: {os.getenv('ALLOWED_ORIGINS')}")
    yield
    logger.info("Shutting down RYZE.AI API")


# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    lifespan=lifespan,
    title="RYZE.AI API",
    description="API for RYZE.AI platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Retrieve allowed origins from the environment
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add this right after your CORS middleware
app.add_middleware(CacheControlMiddleware)

# Register routers with their prefixes
routers_with_prefixes = [
    (register.router, "/auth"),
    (login.router, "/auth"),
    (projects.router, ""),
    (video_upload.router, ""),
    (display_videos.router, ""),
    (requests_router.router, ""),
    (comments.router, ""),
    (conversations.router, ""),
    (profile.router, ""),
    (agreements.router, ""),
    (public_profile.router, ""),
    (feedback.router, ""),
    (payment.router, ""),
    (vote.router, ""),
    (ratings.router, ""),
    (snagged_requests.router, ""),
    (marketplace.router, ""),
]

# Include all routers in this code
for router, prefix in routers_with_prefixes:
    app.include_router(router, prefix=prefix)


@app.get("/debug")
def debug_spaces():
    return {
        "SPACES_BUCKET": os.getenv("SPACES_BUCKET"),
        "SPACES_REGION": os.getenv("SPACES_REGION"),
        "SPACES_KEY": os.getenv("SPACES_KEY"),
        "SPACES_SECRET": os.getenv("SPACES_SECRET"),
    }


@app.get("/test")
def test():
    return {"message": "Server is running"}


@app.get("/routes")
async def get_routes():
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                {
                    "path": route.path,
                    "name": route.name,
                    "methods": list(route.methods),
                    "endpoint": route.endpoint.__name__ if route.endpoint else None,
                    "tags": route.tags,
                }
            )
    routes.sort(key=lambda x: x["path"])
    return {"routes": routes}


# @app.get("/routes-text")
# async def get_routes_text():
#     routes = []
#     for route in app.routes:
#         if isinstance(route, APIRoute):
#             routes.append(f"{', '.join(route.methods)} {route.path}")
#     return PlainTextContent("\n".join(sorted(routes)))


@app.get("/api-test")
async def api_test():
    return JSONResponse(
        content={"status": "ok", "message": "API endpoint working"},
        headers={"Content-Type": "application/json"},
    )


@app.get("/routes-description", response_class=PlainTextResponse)
async def get_routes_description():
    """
    Returns a human-readable description of all the routes in the application.
    """
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(route.methods)
            route_description = (
                f"Path: {route.path}\n"
                f"Methods: {methods}\n"
                f"Name: {route.name}\n"
                f"Tags: {', '.join(route.tags) if route.tags else 'None'}\n"
                f"Endpoint: {route.endpoint.__name__ if route.endpoint else 'None'}\n"
            )
            routes.append(route_description)

    # Join all routes' descriptions into a single plain text response
    return "\n".join(routes)


@app.get("/routes-simple", response_class=PlainTextResponse)
async def get_routes_simple():
    """
    Returns a concise list of all routes with their paths and methods.
    """
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(route.methods)
            routes.append(f"{methods}: {route.path}")

    return "\n".join(routes)
