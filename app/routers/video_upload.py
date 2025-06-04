# app/routers/video_upload.py - Optimized version

import os
import uuid
import logging
import asyncio
from typing import Optional
from pathlib import Path

import boto3
from botocore.config import Config
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Form,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Video, VideoType, User
from app import oauth2
from datetime import datetime

logger = logging.getLogger(__name__)

# Optimized S3 client with better configuration
s3_config = Config(
    region_name=os.getenv("SPACES_REGION"),
    retries={"max_attempts": 3, "mode": "adaptive"},
    max_pool_connections=50,
    # Use multipart uploads for files > 100MB
    multipart_threshold=1024 * 1024 * 100,  # 100MB
    multipart_chunksize=1024 * 1024 * 100,  # 100MB chunks
)

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("SPACES_ENDPOINT"),
    aws_access_key_id=os.getenv("SPACES_KEY"),
    aws_secret_access_key=os.getenv("SPACES_SECRET"),
    config=s3_config,
)

router = APIRouter(prefix="/videos", tags=["Videos"])


async def upload_to_spaces_async(file_path: str, key: str, content_type: str = None):
    """Async upload to Digital Ocean Spaces"""

    def _upload():
        with open(file_path, "rb") as file_obj:
            s3.upload_fileobj(
                file_obj,
                os.getenv("SPACES_BUCKET"),
                key,
                ExtraArgs={
                    "ACL": "public-read",
                    "ContentType": content_type or "video/mp4",
                },
            )

    # Run the blocking upload in a thread pool
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _upload)

    return f"https://{os.getenv('SPACES_BUCKET')}.{os.getenv('SPACES_REGION')}.digitaloceanspaces.com/{key}"


async def process_video_background(
    file_path: str, video_id: int, db_session: Session, compress: bool = True
):
    """Background task for video processing"""
    try:
        if compress:
            # Import here to avoid startup overhead
            from app.utils.video_processor import compress_video

            logger.info(f"Starting compression for video {video_id}")
            compressed_path = compress_video(file_path, "medium")

            # Update the video record with compressed version
            video = db_session.query(Video).filter(Video.id == video_id).first()
            if video:
                # Upload compressed version and update record
                file_extension = os.path.splitext(file_path)[1]
                compressed_key = f"compressed_{uuid.uuid4()}{file_extension}"

                compressed_url = await upload_to_spaces_async(
                    compressed_path, compressed_key, "video/mp4"
                )

                video.file_path = compressed_key
                db_session.commit()

            # Clean up temp files
            if os.path.exists(compressed_path):
                os.remove(compressed_path)

        # Clean up original temp file
        if os.path.exists(file_path):
            os.remove(file_path)

        logger.info(f"Background processing completed for video {video_id}")

    except Exception as e:
        logger.error(f"Background processing failed for video {video_id}: {str(e)}")
    finally:
        db_session.close()


@router.post("/")
async def upload_video(
    background_tasks: BackgroundTasks,
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
    """Optimized video upload with immediate response and background processing"""

    # Generate unique filenames
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = f"/tmp/{unique_filename}"

    try:
        # Stream file to disk efficiently
        with open(temp_file_path, "wb") as buffer:
            chunk_size = 1024 * 1024  # 1MB chunks
            while chunk := await file.read(chunk_size):
                buffer.write(chunk)

        # Create database record immediately (before processing)
        new_video = Video(
            title=title,
            description=description,
            file_path=unique_filename,  # Will be updated after compression
            project_id=project_id,
            request_id=request_id,
            user_id=current_user.id,
            video_type=video_type,
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        # Handle thumbnail upload synchronously (smaller files)
        thumbnail_path = None
        if thumbnail:
            thumbnail_content = await thumbnail.read()
            if thumbnail_content:
                thumbnail_extension = os.path.splitext(thumbnail.filename)[1]
                unique_thumbnail_filename = f"{uuid.uuid4()}{thumbnail_extension}"

                s3.put_object(
                    Bucket=os.getenv("SPACES_BUCKET"),
                    Key=unique_thumbnail_filename,
                    Body=thumbnail_content,
                    ACL="public-read",
                    ContentType=thumbnail.content_type or "image/jpeg",
                )

                thumbnail_path = unique_thumbnail_filename
                new_video.thumbnail_path = thumbnail_path
                db.commit()

        # Start background processing
        # Create new session for background task
        from app.database import SessionLocal

        bg_db = SessionLocal()

        background_tasks.add_task(
            process_video_background,
            temp_file_path,
            new_video.id,
            bg_db,
            True,  # Enable compression
        )

        # Return immediate response
        return JSONResponse(
            content={
                "id": new_video.id,
                "title": new_video.title,
                "description": new_video.description,
                "status": "processing",
                "message": "Video uploaded successfully and is being processed",
            },
            status_code=201,
        )

    except Exception as e:
        logger.error(f"Failed to upload video: {str(e)}")

        # Clean up on error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Remove database record if created
        if "new_video" in locals():
            db.delete(new_video)
            db.commit()

        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")


@router.get("/{video_id}/status")
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user),
):
    """Check if video processing is complete"""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if file exists in spaces (indicates processing complete)
    try:
        s3.head_object(Bucket=os.getenv("SPACES_BUCKET"), Key=video.file_path)
        return {"status": "ready", "video": video}
    except:
        return {"status": "processing"}
