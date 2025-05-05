import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from app import models, schemas, database, oauth2
import aiofiles
import aiohttp
from typing import List
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import uuid
from sqlalchemy.sql import text
from sqlalchemy import func, case
from typing import Optional
from app.database import get_db
from app.models import Video
from app.schemas import (
    DeveloperRatingCreate,
    VideoRatingResponse,
    User,
)
from app.crud import rating as rating_crud
from app.oauth2 import get_current_user

load_dotenv()

# Initialize the logger
logger = logging.getLogger(__name__)

# Load environment variables
SPACES_NAME = os.getenv("SPACES_NAME")
SPACES_REGION = os.getenv("SPACES_REGION")
SPACES_ENDPOINT = f"https://{SPACES_REGION}.digitaloceanspaces.com"
SPACES_BUCKET = os.getenv("SPACES_BUCKET")
SPACES_KEY = os.getenv("SPACES_KEY")
SPACES_SECRET = os.getenv("SPACES_SECRET")


router = APIRouter(prefix="/video_display", tags=["Videos"])

# Initialize the boto3 client
s3 = boto3.client(
    "s3",
    region_name=SPACES_REGION,
    endpoint_url=SPACES_ENDPOINT,
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET,
)


def get_video_by_id(video_id: int, db: Session):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/", response_model=schemas.VideoResponse)
def display_videos(
    db: Session = Depends(database.get_db),
    current_user: Optional[models.User] = Depends(oauth2.get_optional_user),
):
    try:
        # Try to query the Video table - if it doesn't exist yet, handle gracefully
        try:
            videos = db.query(models.Video).all()
        except Exception as e:
            # If table doesn't exist or other DB issue, return empty response
            if "relation" in str(e) or "table" in str(e):
                return schemas.VideoResponse(
                    user_videos=[],
                    other_videos=[],
                )
            else:
                # Re-raise if it's not a missing table error
                raise

        # Early return if no videos
        if not videos:
            return schemas.VideoResponse(
                user_videos=[],
                other_videos=[],
            )

        # Rest of your existing processing code...
        processed_videos = []
        for video in videos:
            try:
                # Count likes
                likes_count = (
                    db.query(models.Vote)
                    .filter(models.Vote.video_id == video.id)
                    .count()
                )

                # Check if current user liked the video
                liked = False
                if current_user:
                    liked = (
                        db.query(models.Vote)
                        .filter(
                            models.Vote.video_id == video.id,
                            models.Vote.user_id == current_user.id,
                        )
                        .first()
                        is not None
                    )

                # Create VideoOut object
                video_out = schemas.VideoOut(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    file_path=video.file_path,
                    thumbnail_path=video.thumbnail_path,
                    upload_date=video.upload_date,
                    project_id=video.project_id,
                    request_id=video.request_id,
                    user_id=video.user_id,
                    video_type=video.video_type,
                    likes=likes_count,
                    liked_by_user=liked,
                )
                processed_videos.append(video_out)

            except Exception as video_error:
                # Log the error but continue processing other videos
                continue

        return schemas.VideoResponse(
            user_videos=[],
            other_videos=processed_videos,
        )

    except Exception as e:
        logger.exception("Error in display_videos endpoint:")
        # Return empty arrays instead of 500 error for better UX with empty DB
        return schemas.VideoResponse(
            user_videos=[],
            other_videos=[],
        )


# Add a new endpoint for authenticated users to get their videos
@router.get("/my-videos", response_model=schemas.VideoResponse)
def get_user_videos(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    try:
        user_videos = (
            db.query(models.Video).filter(models.Video.user_id == current_user.id).all()
        )
        other_videos = (
            db.query(models.Video).filter(models.Video.user_id != current_user.id).all()
        )
        return schemas.VideoResponse(user_videos=user_videos, other_videos=other_videos)
    except Exception as e:

        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/spaces", response_model=List[schemas.SpacesVideoInfo])
async def list_spaces_videos(
    current_user: schemas.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    try:
        # List all objects in the bucket
        response = s3.list_objects_v2(Bucket=SPACES_BUCKET)

        videos = {}
        thumbnails = {}
        base_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com"

        if "Contents" in response:
            for item in response["Contents"]:
                filename = item["Key"]
                file_name, file_extension = os.path.splitext(filename)

                # Extract the UUID from the filename
                try:
                    file_uuid = uuid.UUID(file_name)
                except ValueError:
                    continue  # Skip this file if it's not a valid UUID

                if file_extension.lower() in [".mp4", ".avi", ".mov"]:  # Video formats
                    videos[file_name] = {
                        "filename": filename,
                        "size": item["Size"],
                        "last_modified": item["LastModified"],
                        "url": f"{base_url}/{filename}",
                        "thumbnail_path": None,  # To be matched later
                        "title": None,  # To be retrieved from DB
                        "description": None,  # To be retrieved from DB
                    }
                elif file_extension.lower() in [
                    ".webp",
                    ".jpg",
                    ".png",
                ]:  # Thumbnail formats
                    thumbnails[file_name] = f"{base_url}/{filename}"

        # Match videos with their metadata from the database
        for video_uuid, video_info in videos.items():
            # Fetch metadata using the UUID from the video file name
            query = text(
                "SELECT title, description, thumbnail_path FROM videos WHERE file_path LIKE :pattern"
            )
            result = db.execute(query, {"pattern": f"%{video_uuid}%"}).fetchone()

            # Update video info with metadata if available
            if result:
                video_info["title"] = result.title
                video_info["description"] = result.description
                # If the database contains a thumbnail path, use it; otherwise, we'll assign one later
                if result.thumbnail_path:
                    video_info["thumbnail_path"] = result.thumbnail_path

            # Match the video with a thumbnail from Spaces if not already set
            if not video_info["thumbnail_path"]:
                video_info["thumbnail_path"] = thumbnails.get(
                    video_uuid, "URL_TO_DEFAULT_THUMBNAIL"
                )

        return list(videos.values())

    except ClientError as e:

        raise HTTPException(status_code=500, detail=f"Error listing videos: {str(e)}")


@router.get("/stream/{video_id}")
async def stream_video(
    request: Request, video_id: int = Path(...), db: Session = Depends(database.get_db)
):

    try:
        video = get_video_by_id(video_id, db)

        is_spaces_video = video.file_path.startswith("https://")

        if is_spaces_video:
            # Streaming from Digital Ocean Spaces
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(video.file_path) as response:
                        if response.status != 200:
                            raise HTTPException(
                                status_code=404, detail="Video file not found"
                            )

                        headers = {
                            "Content-Type": response.headers.get(
                                "Content-Type", "video/mp4"
                            ),
                            "Content-Length": response.headers.get(
                                "Content-Length", ""
                            ),
                            "Accept-Ranges": "bytes",
                        }

                        return StreamingResponse(
                            response.content.iter_any(),
                            status_code=200,
                            headers=headers,
                        )
            except aiohttp.ClientError as e:

                raise HTTPException(
                    status_code=500, detail="Error streaming video from cloud storage"
                )
        else:
            # Local file streaming (unchanged)
            if not os.path.exists(video.file_path):

                raise HTTPException(status_code=404, detail="Video file not found")

            file_size = os.path.getsize(video.file_path)

            range_header = request.headers.get("Range")

            start = 0
            end = file_size - 1

            if range_header:
                range_data = range_header.replace("bytes=", "").split("-")
                start = int(range_data[0])
                end = int(range_data[1]) if range_data[1] else file_size - 1

            chunk_size = 1024 * 1024  # 1MB chunks
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Content-Type": "video/mp4",
            }

            async def stream_generator():
                async with aiofiles.open(video.file_path, mode="rb") as video_file:
                    await video_file.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = await video_file.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(
                stream_generator(),
                status_code=206 if range_header else 200,
                headers=headers,
            )

    except HTTPException as he:

        raise he
    except Exception as e:

        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/shared/{share_token}")
async def get_shared_video(share_token: str, db: Session = Depends(get_db)):
    # Get the video by share token
    video = db.query(Video).filter(Video.share_token == share_token).first()

    if not video:
        raise HTTPException(
            status_code=404, detail="Video not found or is no longer shared"
        )

    # Include user information if available
    user_data = None
    if video.user:
        user_data = {
            "id": video.user.id,
            "full_name": video.user.full_name,
            "username": video.user.username,
        }

    return {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "file_path": video.file_path,
        "thumbnail_path": video.thumbnail_path,
        "project_url": video.project_url,
        "upload_date": video.upload_date,
        "user": user_data,
        "user_id": video.user_id,
        "is_public": video.is_public,
    }


@router.post("/{video_id}/rating", response_model=VideoRatingResponse)
async def rate_video(
    video_id: int,
    rating_data: DeveloperRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot rate your own video")

    try:
        # Use the CRUD service
        rating = rating_crud.create_or_update_video_rating(
            db, video_id, current_user.id, rating_data
        )

        stats = rating_crud.get_video_rating_stats(db, video_id)

        # Update the video's aggregate ratings
        video.average_rating = stats["average_rating"]
        video.total_ratings = stats["total_ratings"]
        db.commit()

        return VideoRatingResponse(
            success=True,
            average_rating=stats["average_rating"],
            total_ratings=stats["total_ratings"],
            message="Rating submitted successfully",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
