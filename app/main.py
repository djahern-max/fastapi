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
    conversations,
    profile,
    public_profile,
    request as requests_router,
    feedback,
    payment,
    vote,
    snagged_requests,
    shared_videos,
    project_showcase,
    rating,
    developer_metrics,
    video_ratings,
    external_support,
    collaboration,
    analyticshub_webhook,
    playlists,
    developer_ratings,
)
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import sys
from app.routers import oauth
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from .routers import dynamic_meta


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.endswith((".ico", ".png", ".svg", ".json")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Load environment variables first
load_dotenv(dotenv_path=Path.home() / ".env")

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


# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    lifespan=lifespan,
    title="RYZE.ai API",
    description="API for ireallycode platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Retrieve allowed origins from the environment
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "supersecretkey")
)

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
    (conversations.router, ""),
    (profile.router, ""),
    (public_profile.router, ""),
    (feedback.router, ""),
    (payment.router, ""),
    (vote.router, ""),
    (snagged_requests.router, ""),
    (shared_videos.router, ""),
    (project_showcase.router, ""),
    (rating.router, ""),
    (video_ratings.router, ""),
    (developer_metrics.router, ""),
    (external_support.router, ""),
    (collaboration.router, ""),
    (analyticshub_webhook.router, ""),
    (playlists.router, ""),
    (developer_ratings.router, ""),
    (dynamic_meta.router, ""),
]

# Include all routers in this code
for router, prefix in routers_with_prefixes:
    app.include_router(router, prefix=prefix)

# Include OAuth router
app.include_router(oauth.router)
# Add this line to include the LinkedIn OAuth router


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


@app.get("/test")
async def test_route():
    return {"message": "API is working"}


@app.get("/auth/test-config")
async def test_oauth_config():
    """Test endpoint to check if OAuth environment variables are properly loaded"""
    return {
        "google_client_id_set": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "github_client_id_set": bool(os.getenv("GITHUB_CLIENT_ID")),
        "linkedin_client_id_set": bool(os.getenv("LINKEDIN_CLIENT_ID")),
        "base_url": os.getenv("BASE_URL"),
        "allowed_origins": allowed_origins,
    }
