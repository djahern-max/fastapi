# Standard library imports
import os
import uuid
import logging
from typing import Optional, Dict, Any

# Third-party imports
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, status
from sqlalchemy.orm import Session

# Application imports
from app.database import get_db
from app.models import Video, VideoType, User
from app.schemas import VideoCreate, VideoOut, VideoUpdate
from app import models, oauth2
from app.utils.video_processor import compress_video
from datetime import datetime


# Initialize the logger
logger = logging.getLogger(__name__)

# Load environment variables
SPACES_NAME = os.getenv("SPACES_NAME")
SPACES_REGION = os.getenv("SPACES_REGION")
SPACES_ENDPOINT = os.getenv("SPACES_ENDPOINT")
SPACES_BUCKET = os.getenv("SPACES_BUCKET")
SPACES_KEY = os.getenv("SPACES_KEY")
SPACES_SECRET = os.getenv("SPACES_SECRET")

# Initialize the boto3 client for DigitalOcean Spaces
s3 = boto3.client(
    "s3",
    region_name=SPACES_REGION,
    endpoint_url=SPACES_ENDPOINT,
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET,
)

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post("/")
async def upload_video(
    title: str = Form(...),
    description: str = Form(None),
    project_id: int = Form(None),
    request_id: int = Form(None),
    video_type: VideoType = Form(VideoType.solution_demo),
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user),
):
    # Create temp file paths
    temp_file_path = f"/tmp/{uuid.uuid4()}_{file.filename}"

    try:
        # Save uploaded file to temp location instead of loading into memory
        with open(temp_file_path, "wb") as buffer:
            # Read and write in chunks to handle large files
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                buffer.write(chunk)

        try:
            logger.info(f"Starting video compression for file: {file.filename}")
            # Call the compression function
            compressed_file_path = compress_video(temp_file_path, "medium")
            logger.info(
                f"Compression complete. Original size: {os.path.getsize(temp_file_path) / (1024*1024):.2f}MB, "
                + f"Compressed size: {os.path.getsize(compressed_file_path) / (1024*1024):.2f}MB"
            )
        except Exception as e:
            logger.error(f"Compression failed: {str(e)}. Using original file.")
            compressed_file_path = temp_file_path

        # Initialize S3 client
        s3 = boto3.client(
            "s3",
            region_name=os.getenv("SPACES_REGION"),
            endpoint_url=os.getenv("SPACES_ENDPOINT"),
            aws_access_key_id=os.getenv("SPACES_KEY"),
            aws_secret_access_key=os.getenv("SPACES_SECRET"),
        )

        # Upload video with original extension
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        with open(compressed_file_path, "rb") as video_file:
            s3.put_object(
                Bucket=os.getenv("SPACES_BUCKET"),
                Key=unique_filename,
                Body=video_file,
                ACL="public-read",
                ContentType=file.content_type or "video/mp4",
            )

        file_url = f"https://{os.getenv('SPACES_BUCKET')}.{os.getenv('SPACES_REGION')}.digitaloceanspaces.com/{unique_filename}"

        # Handle thumbnail upload if provided
        thumbnail_path = None
        if thumbnail:
            thumbnail_content = await thumbnail.read()
            if not thumbnail_content:
                raise HTTPException(status_code=400, detail="Thumbnail file is empty")

            thumbnail_extension = os.path.splitext(thumbnail.filename)[1]
            unique_thumbnail_filename = f"{uuid.uuid4()}{thumbnail_extension}"
            thumbnail_content_type = thumbnail.content_type or "image/jpeg"

            s3.put_object(
                Bucket=os.getenv("SPACES_BUCKET"),
                Key=unique_thumbnail_filename,
                Body=thumbnail_content,
                ACL="public-read",
                ContentType=thumbnail_content_type,
            )
            thumbnail_path = f"https://{os.getenv('SPACES_BUCKET')}.{os.getenv('SPACES_REGION')}.digitaloceanspaces.com/{unique_thumbnail_filename}"

        # Save video record in database
        new_video = Video(
            title=title,
            description=description,
            file_path=unique_filename,  # Store just the key, not the full URL
            thumbnail_path=(
                unique_thumbnail_filename if thumbnail_path else None
            ),  # Store just the key
            project_id=project_id,
            request_id=request_id,
            user_id=current_user.id,
            video_type=video_type,
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        # Add the full URLs for the response
        new_video_dict = new_video.__dict__.copy()
        new_video_dict["file_path"] = file_url
        new_video_dict["thumbnail_path"] = thumbnail_path

        return new_video_dict

    except Exception as e:
        logger.error(f"Failed to upload video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

    finally:
        # Clean up temporary files
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/{video_id}/share")
async def generate_share_link(
    video_id: int,
    project_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user),
):
    # Get the video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Update project URL if provided
    if project_url:
        video.project_url = project_url

    # Generate share token if not exists
    if not video.share_token:
        video.share_token = str(uuid.uuid4())

    video.is_public = True
    db.commit()

    base_url = (
        "https://www.ryze.ai"
        if os.getenv("ENV") == "production"
        else "http://localhost:3000"
    )
    share_url = f"{base_url}/shared/videos/{video.share_token}"

    return {"share_url": share_url, "project_url": video.project_url}


def delete_from_spaces(file_key):
    """Delete a file from Digital Ocean Spaces."""
    s3_client = boto3.client(
        "s3",
        region_name=os.getenv("SPACES_REGION"),
        endpoint_url=os.getenv("SPACES_ENDPOINT"),
        aws_access_key_id=os.getenv("SPACES_KEY"),
        aws_secret_access_key=os.getenv("SPACES_SECRET"),
    )

    try:
        # Make sure spaces_name and spaces_bucket are consistent
        bucket_name = os.getenv("SPACES_BUCKET") or os.getenv("SPACES_NAME")
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        logger.info(f"Successfully deleted file {file_key} from Spaces")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_key} from Spaces: {e}")
        raise e


@router.delete("/{video_id}")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Get the video from the database
    video_query = db.query(models.Video).filter(models.Video.id == video_id)
    video = video_query.first()

    # Check if video exists
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found",
        )

    # Check if user owns the video
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this video",
        )

    # Get file paths before deletion
    video_path = video.file_path
    thumbnail_path = video.thumbnail_path

    # Delete from database
    video_query.delete(synchronize_session=False)
    db.commit()

    # Delete from Digital Ocean Spaces
    try:
        # Extract the key (filename) from the full path
        # Make sure this handles your actual path format correctly
        video_key = video_path
        delete_from_spaces(video_key)

        if thumbnail_path:
            thumbnail_key = thumbnail_path
            delete_from_spaces(thumbnail_key)

        return {"message": "Video deleted successfully"}
    except Exception as e:
        # Log the error but don't fail the request
        logger.error(f"Error deleting files from Spaces: {e}")
        return {
            "message": "Video deleted from database but there was an issue removing files from storage"
        }


@router.get("/test")
def test_video_router():
    return {"message": "Video router is working"}


@router.put("/{video_id}", response_model=VideoOut)
def update_video(
    video_id: int,
    video_update: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Get the video
    video_query = db.query(models.Video).filter(models.Video.id == video_id)
    video = video_query.first()

    # Check if video exists
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found",
        )

    # Check if user owns the video
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this video",
        )

    # Update the video with the new data
    for key, value in video_update.model_dump(exclude_unset=True).items():
        setattr(video, key, value)

    # Update timestamp
    video.updated_at = datetime.now()

    # Commit changes to database
    db.commit()
    db.refresh(video)

    return video
