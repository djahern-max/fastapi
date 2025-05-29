from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .. import models, schemas, database, oauth2
from typing import Optional
from fastapi import Body

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/developers/public", response_model=list[schemas.DeveloperProfilePublic])
def get_public_developers(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 500,
    skills: Optional[str] = None,
    min_experience: Optional[int] = None,
):
    """Get list of public developer profiles with optional filtering"""
    try:
        from ..utils.ryze_scoring import RyzeScoring

        # Base query with proper joins
        query = (
            db.query(models.DeveloperProfile)
            .join(models.User, models.DeveloperProfile.user_id == models.User.id)
            .filter(models.DeveloperProfile.is_public == True)
            .options(joinedload(models.DeveloperProfile.user))
        )

        # Apply filters if provided
        if skills:
            query = query.filter(models.DeveloperProfile.skills.ilike(f"%{skills}%"))

        if min_experience is not None:
            query = query.filter(
                models.DeveloperProfile.experience_years >= min_experience
            )

        # Execute query with pagination and sort by success rate (RYZE score)
        developers = (
            query.order_by(models.DeveloperProfile.success_rate.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Ensure all developers have up-to-date RYZE scores
        for developer in developers:
            if developer.success_rate is None or developer.success_rate == 0:
                # Calculate RYZE score if it's missing or zero
                try:
                    ryze_data = RyzeScoring.update_developer_ryze_score(
                        db, developer.id
                    )
                    logger.info(
                        f"Updated RYZE score for developer {developer.user_id}: {ryze_data['success_rate']}%"
                    )
                except Exception as e:
                    logger.error(
                        f"Error updating RYZE score for developer {developer.id}: {str(e)}"
                    )

        logger.info(f"Found {len(developers)} public developers")
        if developers:
            logger.debug(
                f"First developer: {developers[0].id}, User: {developers[0].user.username if developers[0].user else 'No user'}, Success Rate: {developers[0].success_rate}%"
            )

        return developers

    except Exception as e:
        logger.error(f"Error fetching public developers: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching public developers: {str(e)}",
        )


@router.get(
    "/developers/{user_id}/public", response_model=schemas.DeveloperProfilePublic
)
def get_public_developer_profile(user_id: int, db: Session = Depends(database.get_db)):
    """Get a specific public developer profile"""
    profile = (
        db.query(models.DeveloperProfile)
        .filter(
            models.DeveloperProfile.user_id == user_id,
            models.DeveloperProfile.is_public == True,
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Public profile not found"
        )

    return profile


@router.patch("/{id}", response_model=schemas.ConversationOut)
def update_conversation_status(
    id: int,
    status: schemas.ConversationStatus,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    conversation = (
        db.query(models.Conversation).filter(models.Conversation.id == id).first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if user is part of the conversation
    if current_user.id not in [
        conversation.starter_user_id,
        conversation.recipient_user_id,
    ]:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this conversation"
        )

    conversation.status = status
    db.commit()
    db.refresh(conversation)

    return conversation
