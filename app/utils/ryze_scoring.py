# Add this to your FastAPI backend - create app/utils/ryze_scoring.py

import math
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import (
    DeveloperProfile,
    DeveloperRating,
    Showcase,
    ShowcaseRating,
    Video,
    VideoRating,
)


class RyzeScoring:
    """Calculate RYZE scores for developers, showcases, and videos"""

    @staticmethod
    def bayesian_average(
        average_rating: float,
        total_ratings: int,
        confidence_threshold: int = 10,
        global_average: float = 3.0,
    ) -> float:
        """
        Bayesian Average - balances rating quality with quantity
        - Higher ratings with more votes rise to the top
        - Penalizes low sample sizes appropriately
        """
        if total_ratings == 0:
            return 0

        return (
            (confidence_threshold * global_average) + (total_ratings * average_rating)
        ) / (confidence_threshold + total_ratings)

    @staticmethod
    def calculate_success_rate(average_rating: float, total_ratings: int) -> float:
        """
        Calculate success rate (RYZE score) as a percentage
        Higher ratings with more votes = higher success rate
        """
        ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)
        # Convert to percentage (0-100 scale)
        return min(ryze_score * 20, 100)  # Multiply by 20 to convert 0-5 scale to 0-100

    @staticmethod
    def update_developer_ryze_score(db: Session, developer_profile_id: int):
        """Update a developer's RYZE score based on their ratings"""

        # Get rating statistics
        stats = (
            db.query(
                func.avg(DeveloperRating.stars).label("average"),
                func.count(DeveloperRating.id).label("total"),
            )
            .filter(DeveloperRating.developer_id == developer_profile_id)
            .first()
        )

        average_rating = float(stats.average) if stats.average else 0.0
        total_ratings = stats.total

        # Calculate RYZE score
        ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)
        success_rate = RyzeScoring.calculate_success_rate(average_rating, total_ratings)

        # Update the developer profile
        developer = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.id == developer_profile_id)
            .first()
        )
        if developer:
            developer.rating = ryze_score
            developer.success_rate = success_rate
            db.commit()

        return {
            "average_rating": average_rating,
            "total_ratings": total_ratings,
            "ryze_score": ryze_score,
            "success_rate": success_rate,
        }

    @staticmethod
    def update_showcase_ryze_score(db: Session, showcase_id: int):
        """Update a showcase's RYZE score based on its ratings"""

        # Get rating statistics for showcase
        stats = (
            db.query(
                func.avg(ShowcaseRating.stars).label("average"),
                func.count(ShowcaseRating.id).label("total"),
            )
            .filter(ShowcaseRating.showcase_id == showcase_id)
            .first()
        )

        average_rating = float(stats.average) if stats.average else 0.0
        total_ratings = stats.total

        # Calculate RYZE score
        ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)

        # Update the showcase
        showcase = db.query(Showcase).filter(Showcase.id == showcase_id).first()
        if showcase:
            showcase.average_rating = ryze_score
            showcase.total_ratings = total_ratings
            db.commit()

        return {
            "average_rating": average_rating,
            "total_ratings": total_ratings,
            "ryze_score": ryze_score,
        }

    @staticmethod
    def update_video_ryze_score(db: Session, video_id: int):
        """Update a video's RYZE score based on its ratings"""

        # Get rating statistics for video
        stats = (
            db.query(
                func.avg(VideoRating.stars).label("average"),
                func.count(VideoRating.id).label("total"),
            )
            .filter(VideoRating.video_id == video_id)
            .first()
        )

        average_rating = float(stats.average) if stats.average else 0.0
        total_ratings = stats.total

        # Calculate RYZE score
        ryze_score = RyzeScoring.bayesian_average(average_rating, total_ratings)

        # Update the video (you'll need to add these fields to your Video model)
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.average_rating = ryze_score
            video.total_ratings = total_ratings
            db.commit()

        return {
            "average_rating": average_rating,
            "total_ratings": total_ratings,
            "ryze_score": ryze_score,
        }


# Update your developer_ratings.py router to use RYZE scoring
# Add this import to your developer_ratings.py:
from ..utils.ryze_scoring import RyzeScoring


# Then update your rate_developer function to recalculate RYZE scores:
@router.post("/developer/{user_id}", response_model=RatingResponse)
async def rate_developer(
    user_id: int,
    rating_data: DeveloperRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rate a developer by their user ID"""
    try:
        # ... existing code for validation and rating creation ...

        # After creating/updating the rating, update the RYZE score
        ryze_data = RyzeScoring.update_developer_ryze_score(db, developer_profile.id)

        return RatingResponse(
            success=True,
            average_rating=ryze_data[
                "ryze_score"
            ],  # Return the RYZE score, not raw average
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
