from fastapi import FastAPI
import logging
from app.routers import post, user, auth, vote, newsletter
from app.database import engine, Base
from app.config import settings
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

print("Database Username:", settings.database_username)

# Set up logging before application setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    # This line will create all tables that do not exist yet
    Base.metadata.create_all(bind=engine)
    
    # Log all registered routes on application startup
    for route in app.routes:
        logger.info(f"Route: {route.path} | Methods: {route.methods} | Name: {route.name}")

    yield
    logger.info("Application shutdown")

app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ryze.ai",         # Production frontend (apex domain)
        "https://www.ryze.ai",     # Production frontend (www subdomain)
        "http://127.0.0.1:8000",   # Local backend (API)
        "http://localhost:3000",   # Local frontend (React dev server)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(post.router, prefix="/posts", tags=["Posts"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(vote.router, tags=["Votes"])
app.include_router(newsletter.router, prefix="/newsletter", tags=["Newsletter"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ryze (test deploy)!"}

@app.get("/test")
def test():
    return {"message": "Server is running"}

















