from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2
import os
import uuid
import boto3
from fastapi import File, UploadFile
from ..database import get_db
from ..models import User, DeveloperProfile
import logging
from ..oauth2 import get_current_user
from sqlalchemy.orm import joinedload
from fastapi.responses import JSONResponse


# Initialize logger
logger = logging.getLogger(__name__)
# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create handlers
file_handler = logging.FileHandler("app.log")
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

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

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=schemas.UserOut)
def get_profile(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get current user's profile"""
    developer_profile = None
    client_profile = None

    # Convert ORM objects to Pydantic schemas
    if current_user.user_type == models.UserType.developer:
        developer_profile_obj = (
            db.query(models.DeveloperProfile)
            .filter(models.DeveloperProfile.user_id == current_user.id)
            .first()
        )
        if developer_profile_obj:
            developer_profile = schemas.DeveloperProfileOut.model_validate(
                developer_profile_obj
            )

    elif current_user.user_type == models.UserType.client:
        client_profile_obj = (
            db.query(models.ClientProfile)
            .filter(models.ClientProfile.user_id == current_user.id)
            .first()
        )
        if client_profile_obj:
            client_profile = schemas.ClientProfileOut.model_validate(client_profile_obj)

    # Return current user with converted profiles
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "user_type": current_user.user_type,
        "created_at": current_user.created_at,
        "developer_profile": developer_profile,
        "client_profile": client_profile,
    }


@router.get("/developer", response_model=schemas.DeveloperProfileOut)
def get_developer_profile(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get developer profile"""
    if current_user.user_type != models.UserType.developer:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Only developers can access developer profiles."},
        )

    profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "Developer profile not found. Please create a profile to get started.",
                "profile": None,
            },
        )

    return profile


@router.get("/client", response_model=schemas.ClientProfileOut)
def get_client_profile(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get client profile"""
    if current_user.user_type != models.UserType.client:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Only clients can access client profiles."},
        )

    profile = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "Client profile not found. Please create a profile to get started.",
                "profile": None,
            },
        )

    return profile


@router.post(
    "/developer",
    response_model=schemas.DeveloperProfileOut,
    status_code=status.HTTP_201_CREATED,
)
def create_developer_profile(
    profile_data: schemas.DeveloperProfileCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can create developer profiles",
        )

    existing_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists"
        )

    # Initialize with default values for new fields
    profile_data_dict = profile_data.model_dump()
    profile_data_dict.update(
        {
            "user_id": current_user.id,
            "rating": None,
            "total_projects": 0,
            "success_rate": 0.0,
        }
    )

    profile = models.DeveloperProfile(**profile_data_dict)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/client",
    response_model=schemas.ClientProfileOut,
    status_code=status.HTTP_201_CREATED,
)
def create_client_profile(
    profile_data: schemas.ClientProfileCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new client profile"""
    if current_user.user_type != models.UserType.client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can create client profiles",
        )

    # Check if a profile already exists
    existing_profile = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.user_id == current_user.id)
        .first()
    )
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists"
        )

    profile = models.ClientProfile(user_id=current_user.id, **profile_data.dict())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/developer", response_model=schemas.DeveloperProfileOut)
def update_developer_profile(
    profile_update: schemas.DeveloperProfileUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can update developer profiles",
        )

    profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    update_data = profile_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.put("/client", response_model=schemas.ClientProfileOut)
def update_client_profile(
    profile_update: schemas.ClientProfileUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update client profile"""
    if current_user.user_type != models.UserType.client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can update client profiles",
        )

    profile = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    for key, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/developer/image")
async def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    try:
        # First verify that the user is a developer
        if current_user.user_type != models.UserType.developer:
            logger.error(
                f"User {current_user.id} attempted to upload image but is not a developer"
            )
            raise HTTPException(
                status_code=403, detail="Only developers can upload profile images"
            )

        # Log file details
        logger.info(f"Starting image upload for user {current_user.id}")
        logger.debug(
            f"File details - filename: {file.filename}, content_type: {file.content_type}"
        )

        # Verify file is an image
        if not file.content_type.startswith("image/"):
            logger.error(f"Invalid file type attempted: {file.content_type}")
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read file content
        try:
            file_content = await file.read()
            await file.seek(0)  # Reset file position immediately after reading

            if not file_content:
                logger.error("File content is empty")
                raise ValueError("File content is empty")

            logger.debug(
                f"Successfully read file content, size: {len(file_content)} bytes"
            )
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"profile_images/{uuid.uuid4()}{file_extension}"
        logger.info(f"Generated unique filename: {unique_filename}")

        # Upload to DO Spaces
        try:
            s3.put_object(
                Bucket=SPACES_BUCKET,
                Key=unique_filename,
                Body=file_content,  # Make sure file_content is not None
                ACL="public-read",
                ContentType=file.content_type,
            )
            logger.info("Successfully uploaded to Digital Ocean Spaces")
        except Exception as e:
            logger.error(f"Upload to Digital Ocean Spaces failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"profile_images/{uuid.uuid4()}{file_extension}"
        logger.info(f"Generated unique filename: {unique_filename}")

        # Log S3 configuration
        logger.debug(f"S3 Config - Bucket: {SPACES_BUCKET}, Region: {SPACES_REGION}")

        # Upload to DO Spaces
        try:
            s3.put_object(
                Bucket=SPACES_BUCKET,
                Key=unique_filename,
                Body=file_content,
                ACL="public-read",
                ContentType=file.content_type,
            )
            logger.info("Successfully uploaded to Digital Ocean Spaces")
        except Exception as e:
            logger.error(f"Upload to Digital Ocean Spaces failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

        # Generate image URL
        image_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{unique_filename}"
        logger.info(f"Generated image URL: {image_url}")

        # Update database
        try:
            developer_profile = (
                db.query(models.DeveloperProfile)
                .filter(models.DeveloperProfile.user_id == current_user.id)
                .first()
            )

            if developer_profile:
                logger.debug(
                    f"Current profile image URL: {developer_profile.profile_image_url}"
                )
                developer_profile.profile_image_url = image_url
                db.commit()
                db.refresh(developer_profile)
                logger.info(
                    f"Updated profile with new image URL: {developer_profile.profile_image_url}"
                )
            else:
                logger.warning(f"No developer profile found for user {current_user.id}")

        except Exception as e:
            logger.error(f"Database update failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Database update failed: {str(e)}"
            )

        return {"image_url": image_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_profile_image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.seek(0)


@router.get("/developers/public", response_model=list[schemas.DeveloperProfilePublic])
def get_public_developers(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 100,
    skills: Optional[str] = None,
    min_experience: Optional[int] = None,
):
    """Get all public developer profiles with their user information and optional filtering"""
    try:
        query = (
            db.query(models.DeveloperProfile)
            .join(models.User)  # Join with the User table
            .filter(models.DeveloperProfile.is_public == True)
            .options(
                joinedload(models.DeveloperProfile.user)
            )  # Fixed joinedload syntax
        )

        # Apply filters if provided
        if skills:
            # Case-insensitive search for skills
            query = query.filter(models.DeveloperProfile.skills.ilike(f"%{skills}%"))

        if min_experience is not None:
            query = query.filter(
                models.DeveloperProfile.experience_years >= min_experience
            )

        developers = query.offset(skip).limit(limit).all()
        return developers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching public developers: {str(e)}",
        )


@router.get("/check-profile", response_model=schemas.ProfileCheckResponse)
def check_user_profile(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Check if the current user has a profile"""
    result = {"has_profile": False, "profile_type": None, "profile_id": None}

    if current_user.user_type == models.UserType.developer:
        profile = (
            db.query(models.DeveloperProfile)
            .filter(models.DeveloperProfile.user_id == current_user.id)
            .first()
        )
        if profile:
            result["has_profile"] = True
            result["profile_type"] = "developer"
            result["profile_id"] = profile.id

    elif current_user.user_type == models.UserType.client:
        profile = (
            db.query(models.ClientProfile)
            .filter(models.ClientProfile.user_id == current_user.id)
            .first()
        )
        if profile:
            result["has_profile"] = True
            result["profile_type"] = "client"
            result["profile_id"] = profile.id

    return result
