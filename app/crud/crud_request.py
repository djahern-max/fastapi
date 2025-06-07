from sqlalchemy.orm import joinedload, Session
from sqlalchemy import and_
from typing import Optional
from fastapi import HTTPException
import re
from app import models, schemas
from sqlalchemy.orm import joinedload, contains_eager
from typing import Optional
from app import models, schemas
from sqlalchemy.orm import joinedload, contains_eager
from sqlalchemy import and_
from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional
from app.models import Request
from app.schemas import RequestUpdate
from sqlalchemy.orm import joinedload, contains_eager
from sqlalchemy import and_
from fastapi import HTTPException
from datetime import datetime
from app.models import Request, User

# ------------------ Utility Functions ------------------


def has_edit_permission(db: Session, request: models.Request, user_id: int) -> bool:
    """Check if a user has permission to edit a request."""
    return (
        request.user_id == user_id
        or db.query(models.RequestShare)
        .filter(
            and_(
                models.RequestShare.request_id == request.id,
                models.RequestShare.shared_with_user_id == user_id,
                models.RequestShare.can_edit == True,
            )
        )
        .first()
    )


# ------------------ CRUD Operations ------------------


def create_request(db: Session, request: schemas.RequestCreate, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    db_request = models.Request(
        title=request.title,
        content=request.content,
        project_id=request.project_id,
        user_id=user_id,
        is_public=request.is_public,  # This should be the source of truth
        estimated_budget=request.estimated_budget,
        is_idea=request.is_idea,
        seeks_collaboration=request.seeks_collaboration,
        collaboration_details=request.collaboration_details,
    )

    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    # If developer_id is provided, automatically create a share
    if hasattr(request, "developer_id") and request.developer_id:
        db_share = models.RequestShare(
            request_id=db_request.id,
            shared_with_user_id=request.developer_id,
            can_edit=False,
        )
        db.add(db_share)
        db.commit()

    # Add the video relationship if video_id is provided
    if hasattr(request, "video_id") and request.video_id:
        video = (
            db.query(models.Video).filter(models.Video.id == request.video_id).first()
        )
        if video:
            video.request_id = db_request.id
            db.commit()

    # Add the owner_username to the response
    setattr(db_request, "owner_username", user.username)
    return db_request


def get_public_requests(
    db: Session, skip: int = 0, limit: int = 100, developer_id: Optional[int] = None
):
    # Base query for public requests
    query = db.query(models.Request).filter(models.Request.is_public == True)

    if developer_id:
        # Filter by developer_id if provided
        pass

    requests = query.offset(skip).limit(limit).all()

    return requests


def get_request_by_id(db: Session, request_id: int):
    """Retrieve a specific request by its ID."""
    request = (
        db.query(models.Request)
        .join(
            models.User, models.Request.user_id == models.User.id
        )  # Join with User table
        .filter(models.Request.id == request_id)
        .first()
    )

    if request:
        # Add the owner's username to the request object
        owner = db.query(models.User).filter(models.User.id == request.user_id).first()
        setattr(request, "owner_username", owner.username if owner else "Unknown")

    return request


def update_request(
    db: Session, request_id: int, request_update: RequestUpdate, user_id: int
):
    """Update a request with partial data."""

    # Get the existing request
    request = (
        db.query(Request)
        .filter(Request.id == request_id, Request.user_id == user_id)
        .first()
    )

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Get the owner info
    owner = db.query(User).filter(User.id == request.user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Request owner not found")

    # Convert update data to dict, excluding None values
    update_data = request_update.model_dump(exclude_unset=True, exclude_none=True)

    # Handle status update specifically
    if "status" in update_data:
        request.status = update_data["status"]

    # Handle other fields
    for field, value in update_data.items():
        if field != "status":  # Skip status as we handled it above
            # Remove this check:
            # if field == "content" and value is not None:
            #     request.contains_sensitive_data = check_sensitive_content(value)
            setattr(request, field, value)

    try:
        db.commit()
        print("Database commit successful")
        db.refresh(request)

        # Create response with required fields
        response_dict = {
            "id": request.id,
            "title": request.title,
            "content": request.content,
            "user_id": request.user_id,
            "status": request.status,
            "project_id": request.project_id,
            "is_public": request.is_public,
            # Remove this line:
            # "contains_sensitive_data": request.contains_sensitive_data,
            "estimated_budget": request.estimated_budget,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "owner_username": owner.username,
            "shared_with_info": [],
            "is_idea": request.is_idea,
            "seeks_collaboration": request.seeks_collaboration,
            "collaboration_details": request.collaboration_details,
        }

        return response_dict

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ------------------ Sharing Functionality ------------------


def share_request(
    db: Session, request_id: int, user_id: int, share: schemas.RequestShare
):
    """Share a request with another user."""  # Updated comment
    request = get_request_by_id(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to share this request"
        )

    # Remove this check:
    # if request.contains_sensitive_data:
    #     raise HTTPException(
    #         status_code=400, detail="Cannot share requests containing sensitive data"
    #     )

    existing_share = (
        db.query(models.RequestShare)
        .filter(
            and_(
                models.RequestShare.request_id == request_id,
                models.RequestShare.shared_with_user_id == share.shared_with_user_id,
            )
        )
        .first()
    )

    if existing_share:
        raise HTTPException(
            status_code=400, detail="Request is already shared with this user"
        )

    db_share = models.RequestShare(
        request_id=request_id,
        shared_with_user_id=share.shared_with_user_id,
        can_edit=share.can_edit,
    )
    db.add(db_share)
    db.commit()
    db.refresh(db_share)
    return db_share


def remove_share(db: Session, request_id: int, user_id: int, shared_user_id: int):
    """Remove sharing of a request for a specific user, ensuring ownership."""
    request = get_request_by_id(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to modify sharing settings for this request",
        )

    share = (
        db.query(models.RequestShare)
        .filter(
            and_(
                models.RequestShare.request_id == request_id,
                models.RequestShare.shared_with_user_id == shared_user_id,
            )
        )
        .first()
    )

    if share:
        db.delete(share)
        db.commit()
    return share


def get_shared_requests(db: Session, user_id: int):
    """Get all requests shared with the user."""
    return (
        db.query(models.Request)
        .join(models.RequestShare, models.Request.id == models.RequestShare.request_id)
        .filter(models.RequestShare.shared_with_user_id == user_id)
        .all()
    )


def toggle_request_privacy(db: Session, request_id: int, user_id: int, is_public: bool):
    """Toggle the privacy of a request, ensuring ownership."""
    request = get_request_by_id(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this request"
        )

    request.is_public = is_public
    db.commit()
    db.refresh(request)
    return request


# Add these at the bottom of your crud_request.py file


def get_request_shares(db: Session, request_id: int) -> List[models.User]:
    """Get all users that a request is shared with."""
    return (
        db.query(models.User)
        .join(
            models.RequestShare,
            models.RequestShare.shared_with_user_id == models.User.id,
        )
        .filter(models.RequestShare.request_id == request_id)
        .all()
    )


def add_request_to_project(db: Session, request_id: int, project_id: int, user_id: int):
    # Get the request and verify ownership
    request = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this request"
        )

    # Get the project and verify ownership
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to add to this project"
        )

    # Get the owner's username
    owner = db.query(models.User).filter(models.User.id == request.user_id).first()

    # Update the request
    request.project_id = project_id
    request.added_to_project_at = datetime.utcnow()

    db.commit()
    db.refresh(request)

    # Add owner_username to the response
    setattr(request, "owner_username", owner.username)

    return request


def remove_request_from_project(db: Session, request_id: int, user_id: int):
    """Remove a request from its project."""
    request = get_request_by_id(db, request_id)
    if not request or request.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this request"
        )

    request.project_id = None
    request.added_to_project_at = None
    db.commit()
    db.refresh(request)
    return request


def is_request_shared_with_user(db: Session, request_id: int, user_id: int) -> bool:
    """
    Check if a request is shared with a specific user.

    Args:
        db (Session): Database session
        request_id (int): ID of the request to check
        user_id (int): ID of the user to check

    Returns:
        bool: True if the request is shared with the user, False otherwise
    """
    share = (
        db.query(models.RequestShare)
        .filter(
            and_(
                models.RequestShare.request_id == request_id,
                models.RequestShare.shared_with_user_id == user_id,
            )
        )
        .first()
    )
    return share is not None


def get_requests_by_user(
    db: Session,
    user_id: int,
    project_id: Optional[int] = None,
    include_shared: bool = True,
    skip: int = 0,
    limit: int = 100,
):
    """
    Get requests for a specific user with optional project filtering.

    Parameters:
    - db: Database session
    - user_id: ID of the user whose requests to retrieve
    - project_id: Optional filter for requests belonging to a specific project
    - include_shared: Whether to include requests shared with the user
    - skip: Number of items to skip (pagination)
    - limit: Maximum number of items to return (pagination)

    Returns:
    - List of Request objects with additional attributes (owner_username, shared_with_info)
    """
    try:
        # Base query for user's own requests
        query = (
            db.query(models.Request)
            .join(models.User, models.Request.user_id == models.User.id)
            .options(contains_eager(models.Request.user))
            .options(
                joinedload(models.Request.shared_with).joinedload(
                    models.RequestShare.user
                )
            )
            .filter(
                models.Request.user_id == user_id
            )  # Get all user's requests regardless of public status
        )

        if project_id:
            query = query.filter(models.Request.project_id == project_id)

        # Add ordering for consistent results
        query = query.order_by(models.Request.created_at.desc())

        requests = query.offset(skip).limit(limit).all()

        # Transform the requests
        for request in requests:
            # Always set owner_username regardless of public status
            request.owner_username = request.user.username
            # Create shared_with_info list for each request
            request.shared_with_info = []
            for share in request.shared_with:
                if hasattr(share, "user"):
                    request.shared_with_info.append(
                        {
                            "user_id": share.user.id,
                            "username": share.user.username,
                            "can_edit": share.can_edit,
                        }
                    )

        # If include_shared is True, also get requests shared with the user
        if include_shared:
            shared_requests = (
                db.query(models.Request)
                .join(
                    models.RequestShare,
                    models.Request.id == models.RequestShare.request_id,
                )
                .join(models.User, models.Request.user_id == models.User.id)
                .options(contains_eager(models.Request.user))
                .options(
                    joinedload(models.Request.shared_with).joinedload(
                        models.RequestShare.user
                    )
                )
                .filter(models.RequestShare.shared_with_user_id == user_id)
                .order_by(models.Request.created_at.desc())
                .all()
            )

            # Transform the shared requests
            for request in shared_requests:
                # Set owner_username
                request.owner_username = request.user.username

                # Create shared_with_info list for each request
                request.shared_with_info = []
                for share in request.shared_with:
                    if hasattr(share, "user"):
                        request.shared_with_info.append(
                            {
                                "user_id": share.user.id,
                                "username": share.user.username,
                                "can_edit": share.can_edit,
                            }
                        )

            # We need to avoid duplicates if the user has shared a request with themselves
            shared_request_ids = {r.id for r in requests}
            unique_shared_requests = [
                r for r in shared_requests if r.id not in shared_request_ids
            ]
            requests.extend(unique_shared_requests)

            # Re-sort the combined list
            requests.sort(key=lambda r: r.created_at, reverse=True)

            # Apply limit after combining (if we're not beyond it already)
            if len(requests) > limit:
                requests = requests[:limit]

        return requests
    except Exception as e:
        print(f"Error in get_requests_by_user: {str(e)}")
        raise


# In app/crud/crud_request.py or similar file
def get_request_by_external_id(db: Session, external_id: int):
    """Get a request by its external ID (from external_metadata)"""
    return db.query(models.Request).filter(models.Request.id == external_id).first()


# In app/crud/crud_conversation.py or similar file
def get_conversation_by_request_id(db: Session, request_id: int):
    """Get the conversation associated with a request"""
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.request_id == request_id)
        .first()
    )


def create_conversation_message(
    db: Session,
    conversation_id: int,
    user_id: int,
    content: str,
    external_source: str = None,
):
    """Create a new message in a conversation, optionally from an external source"""
    message = models.ConversationMessage(
        conversation_id=conversation_id,
        user_id=user_id,
        content=content,
        # If your model has these fields, include them
        external_source=external_source,
        # Add any other required fields
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
