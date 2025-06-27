import sys


from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from ..oauth2 import get_current_user
from ..crud import rating as rating_crud
from ..crud.project_showcase import (  # Make sure this import is correct
    create_project_showcase,
    get_project_showcase,
    get_developer_showcases,
    update_project_showcase,
    delete_project_showcase,
)
from ..models import (
    DeveloperProfile,
    Showcase,
    User,  # Added User model import
)
from ..schemas import (
    DeveloperRatingCreate,
    DeveloperRatingOut,
    DeveloperRatingStats,
    RatingResponse,
    ProjectShowcase,
    ProjectShowcaseCreate,
)
import logging


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/project-showcase", tags=["Projet Showcase"])


@router.post("/", response_model=ProjectShowcase)
async def create_showcase(
    title: str = Form(...),
    description: str = Form(...),
    project_url: Optional[str] = Form(None),
    repository_url: Optional[str] = Form(None),
    demo_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    readme_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        if image_file and not image_file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Please upload an image file.",
            )

        if readme_file and not readme_file.filename.endswith(".md"):
            raise HTTPException(
                status_code=400, detail="README file must be a markdown (.md) file"
            )

        showcase_data = ProjectShowcaseCreate(
            title=title,
            description=description,
            project_url=project_url,
            repository_url=repository_url,
            demo_url=demo_url,
        )

        showcase = create_project_showcase(
            db=db,
            showcase=showcase_data,
            developer_id=current_user.id,
            image_file=image_file,
            readme_file=readme_file,
        )

        return showcase

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/developer/{developer_id}", response_model=RatingResponse)
async def rate_developer(
    developer_id: int,
    rating_data: DeveloperRatingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Get developer profile
    developer = (
        db.query(DeveloperProfile)
        .filter(DeveloperProfile.user_id == developer_id)
        .first()
    )
    if not developer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    rating = rating_crud.create_or_update_rating(
        db,
        developer.id,  # Use developer profile ID
        current_user.id,  # Use current user's ID directly
        rating_data,
    )

    stats = rating_crud.get_developer_rating_stats(db, developer.id)

    return {
        "success": True,
        "average_rating": stats.average_rating,
        "total_ratings": stats.total_ratings,
        "message": (
            "Rating updated successfully" if rating else "Rating added successfully"
        ),
    }


@router.get("/developer/{developer_id}", response_model=List[ProjectShowcase])
async def get_developer_showcases(
    developer_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    try:
        # Fix: Don't call itself - use the imported crud function directly
        showcases = await get_developer_showcases(db, developer_id, skip, limit)
        return showcases or []
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/developer/{developer_id}/user-rating", response_model=Optional[DeveloperRatingOut]
)
async def get_user_rating(
    developer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    developer = (
        db.query(DeveloperProfile)
        .filter(DeveloperProfile.user_id == developer_id)
        .first()
    )
    if not developer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    return rating_crud.get_user_rating(db, developer.id, current_user.id)


@router.get("/developer/{developer_id}/rating", response_model=DeveloperRatingStats)
async def get_developer_rating_by_user_id(
    developer_id: int, db: Session = Depends(get_db)
):
    # First get the developer profile using the user_id
    developer = (
        db.query(DeveloperProfile)
        .filter(DeveloperProfile.user_id == developer_id)
        .first()
    )
    if not developer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    try:
        stats = rating_crud.get_developer_rating_stats(db, developer.id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting developer rating: {str(e)}",
        )


@router.post("/showcase/{showcase_id}", response_model=RatingResponse)
async def rate_showcase(
    showcase_id: int,
    rating_data: DeveloperRatingCreate,  # We can reuse this schema
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    showcase = db.query(Showcase).filter(Showcase.id == showcase_id).first()
    if not showcase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Showcase not found"
        )

    # Check if user is trying to rate their own showcase
    if showcase.developer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot rate your own showcase",
        )

    rating = rating_crud.create_or_update_showcase_rating(
        db,
        showcase_id,
        current_user.id,
        rating_data,
    )

    stats = rating_crud.get_showcase_rating_stats(db, showcase_id)

    return {
        "success": True,
        "average_rating": stats.average_rating,
        "total_ratings": stats.total_ratings,
        "message": (
            "Rating updated successfully" if rating else "Rating added successfully"
        ),
    }


@router.get("/showcase/{showcase_id}", response_model=DeveloperRatingStats)
async def get_showcase_rating(showcase_id: int, db: Session = Depends(get_db)):
    showcase = db.query(Showcase).filter(Showcase.id == showcase_id).first()
    if not showcase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Showcase not found"
        )
    return rating_crud.get_showcase_rating_stats(db, showcase_id)


@router.get(
    "/showcase/{showcase_id}/user-rating", response_model=Optional[DeveloperRatingOut]
)
async def get_showcase_user_rating(
    showcase_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    showcase = db.query(Showcase).filter(Showcase.id == showcase_id).first()
    if not showcase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Showcase not found"
        )

    return rating_crud.get_showcase_user_rating(db, showcase_id, current_user.id)
