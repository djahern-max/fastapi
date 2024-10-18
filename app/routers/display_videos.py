import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from app import schemas, oauth2
from typing import List
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

# Initialize the logger
logger = logging.getLogger(__name__)

# Load environment variables
SPACES_REGION = os.getenv('SPACES_REGION')
SPACES_ENDPOINT = f"https://{SPACES_REGION}.digitaloceanspaces.com"
SPACES_BUCKET = os.getenv('SPACES_BUCKET')
SPACES_KEY = os.getenv('SPACES_KEY')
SPACES_SECRET = os.getenv('SPACES_SECRET')

router = APIRouter(
    prefix="/video_display",
    tags=["Videos"]
)

# Initialize the boto3 client
s3 = boto3.client('s3',
                  region_name=SPACES_REGION,
                  endpoint_url=SPACES_ENDPOINT,
                  aws_access_key_id=SPACES_KEY,
                  aws_secret_access_key=SPACES_SECRET)

@router.get("/spaces", response_model=List[schemas.SpacesVideoInfo])
async def list_spaces_videos(current_user: schemas.User = Depends(oauth2.get_current_user)):
    try:
        logger.info(f"Listing objects in bucket: {SPACES_BUCKET}")
        
        response = s3.list_objects_v2(Bucket=SPACES_BUCKET)
        
        videos = []
        
        if 'Contents' in response:
            logger.info(f"Found {len(response['Contents'])} objects in the bucket")
            for item in response['Contents']:
                filename = item['Key']
                file_extension = os.path.splitext(filename)[1].lower()
                
                if file_extension in ['.mp4', '.avi', '.mov']:  # Video formats
                    video_name = os.path.splitext(filename)[0]
                    video_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{filename}"
                    thumbnail_url = get_thumbnail_url(video_name)
                    
                    videos.append({
                        'filename': filename,
                        'size': item['Size'],
                        'last_modified': item['LastModified'],
                        'url': video_url,
                        'thumbnail_path': thumbnail_url
                    })
                    logger.info(f"Added video: {filename}")

        logger.info(f"Returning {len(videos)} video entries")
        return videos

    except ClientError as e:
        logger.error(f"Error listing videos from Spaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing videos: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

def get_thumbnail_url(video_name):
    thumbnail_extensions = ['.webp', '.jpg', '.png']
    
    for ext in thumbnail_extensions:
        thumbnail_filename = f"{video_name}{ext}"
        try:
            s3.head_object(Bucket=SPACES_BUCKET, Key=thumbnail_filename)
            return f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{thumbnail_filename}"
        except ClientError:
            continue
    
    return None

@router.get("/thumbnail/{video_filename}")
async def get_thumbnail(video_filename: str):
    try:
        logger.info(f"Attempting to retrieve thumbnail for video: {video_filename}")

        video_name = os.path.splitext(video_filename)[0]
        thumbnail_url = get_thumbnail_url(video_name)

        if thumbnail_url:
            logger.info(f"Thumbnail found: {thumbnail_url}")
            return {"thumbnail_url": thumbnail_url}
        else:
            logger.error(f"No thumbnail found for video: {video_filename}")
            raise HTTPException(status_code=404, detail="Thumbnail not found")

    except Exception as e:
        logger.error(f"Error retrieving thumbnail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving thumbnail: {str(e)}")