from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..oauth2 import get_current_user
from ..models import User, DeveloperProfile, DeveloperRating
from ..schemas import (
    DeveloperRatingCreate,
    DeveloperRatingOut,
    DeveloperRatingStats,
    RatingResponse,
)
from sqlalchemy import func
import logging
from ..utils.ryze_scoring import RyzeScoring

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ratings", tags=["Developer Ratings"])


@router.post("/developer/{user_id}", response_model=RatingResponse)
async def rate_developer(
    user_id: int,
    rating_data: DeveloperRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rate a developer by their user ID"""
    try:
        # Verify the user exists and is a developer
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if target_user.user_type.value != "developer":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a developer",
            )

        # Get the developer profile
        developer_profile = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.user_id == user_id)
            .first()
        )

        if not developer_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer profile not found",
            )

        # Prevent self-rating
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot rate yourself",
            )

        # Check if rating already exists
        existing_rating = (
            db.query(DeveloperRating)
            .filter(
                DeveloperRating.developer_id == developer_profile.id,
                DeveloperRating.user_id == current_user.id,
            )
            .first()
        )

        if existing_rating:
            # Update existing rating
            existing_rating.stars = rating_data.stars
            existing_rating.comment = rating_data.comment
            db.commit()
            db.refresh(existing_rating)
            logger.info(
                f"Updated rating for developer {user_id} by user {current_user.id}"
            )
            action = "updated"
        else:
            # Create new rating
            new_rating = DeveloperRating(
                developer_id=developer_profile.id,
                user_id=current_user.id,
                stars=rating_data.stars,
                comment=rating_data.comment,
            )
            db.add(new_rating)
            db.commit()
            db.refresh(new_rating)
            logger.info(
                f"Created new rating for developer {user_id} by user {current_user.id}"
            )
            action = "added"

        # Update RYZE Score after rating is added/updated
        ryze_data = RyzeScoring.update_developer_ryze_score(db, developer_profile.id)
        logger.info(f"Updated RYZE score for developer {user_id}: {ryze_data}")

        return RatingResponse(
            success=True,
            average_rating=ryze_data[
                "ryze_score"
            ],  # Return RYZE score instead of raw average
            total_ratings=ryze_data["total_ratings"],
            message=f"Rating {action} successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rating developer {user_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while submitting the rating",
        )


@router.get("/developer/{user_id}/rating", response_model=DeveloperRatingStats)
async def get_developer_rating_stats(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get rating statistics for a developer by their user ID"""
    try:
        # Get the developer profile
        developer_profile = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.user_id == user_id)
            .first()
        )

        if not developer_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer profile not found",
            )

        # Use the helper function to get comprehensive stats
        stats = get_developer_rating_stats_helper(db, developer_profile.id)

        # The stats will now include the RYZE score as the average_rating
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rating stats for developer {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching rating statistics",
        )


@router.get(
    "/developer/{user_id}/user-rating", response_model=Optional[DeveloperRatingOut]
)
async def get_user_developer_rating(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's rating for a specific developer"""
    try:
        # Get the developer profile
        developer_profile = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.user_id == user_id)
            .first()
        )

        if not developer_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer profile not found",
            )

        # Get the user's rating for this developer
        user_rating = (
            db.query(DeveloperRating)
            .filter(
                DeveloperRating.developer_id == developer_profile.id,
                DeveloperRating.user_id == current_user.id,
            )
            .first()
        )

        return user_rating

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user rating for developer {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user rating",
        )


def get_developer_rating_stats_helper(
    db: Session, developer_profile_id: int
) -> DeveloperRatingStats:
    """
    Helper function to calculate rating statistics for a developer profile
    Now returns RYZE score instead of raw average rating
    """
    # Get raw rating statistics
    stats = (
        db.query(
            func.avg(DeveloperRating.stars).label("average"),
            func.count(DeveloperRating.id).label("total"),
        )
        .filter(DeveloperRating.developer_id == developer_profile_id)
        .first()
    )

    raw_average = float(stats.average) if stats.average else 0.0
    total_ratings = stats.total

    # Calculate RYZE score using Bayesian Average
    ryze_score = RyzeScoring.bayesian_average(raw_average, total_ratings)

    # Get rating distribution (this remains the same for detailed analytics)
    distribution = dict.fromkeys(range(1, 6), 0)
    ratings = (
        db.query(DeveloperRating.stars, func.count(DeveloperRating.id))
        .filter(DeveloperRating.developer_id == developer_profile_id)
        .group_by(DeveloperRating.stars)
        .all()
    )

    for rating, count in ratings:
        distribution[rating] = count

    return DeveloperRatingStats(
        average_rating=ryze_score,  # Return RYZE score instead of raw average
        total_ratings=total_ratings,
        rating_distribution=distribution,
    )


@router.get("/developer/{user_id}/ryze-score")
async def get_developer_ryze_score(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed RYZE score information for a developer
    This endpoint provides both the RYZE score and success rate percentage
    """
    try:
        # Get the developer profile
        developer_profile = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.user_id == user_id)
            .first()
        )

        if not developer_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer profile not found",
            )

        # Get raw statistics
        stats = (
            db.query(
                func.avg(DeveloperRating.stars).label("average"),
                func.count(DeveloperRating.id).label("total"),
            )
            .filter(DeveloperRating.developer_id == developer_profile.id)
            .first()
        )

        raw_average = float(stats.average) if stats.average else 0.0
        total_ratings = stats.total

        # Calculate RYZE metrics
        ryze_score = RyzeScoring.bayesian_average(raw_average, total_ratings)
        success_rate = RyzeScoring.calculate_success_rate(raw_average, total_ratings)

        return {
            "user_id": user_id,
            "raw_average_rating": raw_average,
            "total_ratings": total_ratings,
            "ryze_score": ryze_score,
            "success_rate_percentage": success_rate,
            "explanation": f"RYZE Score combines rating quality ({raw_average:.1f}/5) with quantity ({total_ratings} ratings) to fairly rank developers",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting RYZE score for developer {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching RYZE score",
        )
