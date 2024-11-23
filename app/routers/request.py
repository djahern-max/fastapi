from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.crud import crud_request, crud_user
from app import schemas, models
from app.models import UserType
from ..database import get_db
from ..oauth2 import get_current_user, get_optional_user
from fastapi.encoders import jsonable_encoder
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/requests", tags=["Requests"])

# ------------------ Shared and Public Requests ------------------


@router.get("/public", response_model=List[schemas.RequestOut])
def get_public_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    """Get all public requests optionally filtering for developer-specific results."""
    try:
        logger.info("Fetching public requests")
        logger.info(f"Current user: {current_user.id if current_user else 'None'}")

        # Get public requests
        requests = (
            db.query(models.Request)
            .filter(models.Request.is_public == True)
            .order_by(models.Request.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Get usernames for each request
        result = []
        for request in requests:
            owner = db.query(models.User).filter(models.User.id == request.user_id).first()
            request_dict = {
                "id": request.id,
                "title": request.title,
                "content": request.content,
                "project_id": request.project_id,
                "user_id": request.user_id,
                "owner_username": owner.username if owner else "Unknown",
                "is_public": request.is_public,
                "status": request.status,
                "estimated_budget": request.estimated_budget,
                "created_at": request.created_at,
                "updated_at": request.updated_at,
                "contains_sensitive_data": request.contains_sensitive_data,
                "shared_with_info": [],
            }
            result.append(request_dict)

        logger.info(f"Found {len(result)} public requests")
        return result

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_public_requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_public_requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred"
        )


@router.get("/shared-with-me", response_model=List[schemas.SharedRequestOut])
def get_shared_requests(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Get all requests shared with the current user."""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(status_code=403, detail="Only developers can access shared requests")

    # Build the query with all necessary fields
    shared_requests = (
        db.query(
            models.Request,
            models.RequestShare.id.label("share_id"),
            models.RequestShare.viewed_at,
            models.RequestShare.created_at.label("share_date"),
            models.User.username.label("owner_username"),
        )
        .join(models.RequestShare, models.Request.id == models.RequestShare.request_id)
        .join(models.User, models.Request.user_id == models.User.id)
        .filter(models.RequestShare.shared_with_user_id == current_user.id)
        .all()
    )

    response_data = []
    for request, share_id, viewed_at, share_date, owner_username in shared_requests:
        request_dict = {
            "id": request.id,
            "title": request.title,
            "content": request.content,
            "project_id": request.project_id,
            "user_id": request.user_id,
            "owner_username": owner_username,
            "is_public": request.is_public,
            "status": request.status,
            "estimated_budget": request.estimated_budget,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "contains_sensitive_data": request.contains_sensitive_data,
            "shared_with_info": [],
            "is_new": viewed_at is None,
            "share_id": share_id,
            "share_date": share_date,
        }
        response_data.append(request_dict)

    return response_data


@router.post("/shared-with-me/{share_id}/mark-viewed")
def mark_share_viewed(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a shared request as viewed."""
    share = (
        db.query(models.RequestShare)
        .filter(
            models.RequestShare.id == share_id,
            models.RequestShare.shared_with_user_id == current_user.id,
        )
        .first()
    )

    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    share.viewed_at = func.now()
    db.commit()

    return {"success": True}


@router.post("/shared-with-me/{share_id}/mark-viewed")
def mark_share_viewed(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a shared request as viewed."""
    share = (
        db.query(models.RequestShare)
        .filter(
            models.RequestShare.id == share_id,
            models.RequestShare.shared_with_user_id == current_user.id,
        )
        .first()
    )

    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    share.viewed_at = func.now()
    db.commit()

    return {"success": True}


# ------------------ CRUD Operations ------------------


@router.post("/", response_model=schemas.RequestOut)
def create_request(
    request: schemas.RequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new request, restricted to clients."""
    if current_user.user_type != UserType.client:
        raise HTTPException(status_code=403, detail="Only clients can create requests")
    return crud_request.create_request(db=db, request=request, user_id=current_user.id)


# Add this to your get_requests endpoint in request.py
@router.get("/", response_model=List[schemas.SimpleRequestOut])
def get_requests(
    request: Request,
    project_id: Optional[int] = None,
    include_shared: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        requests = crud_request.get_requests_by_user(
            db=db,
            user_id=current_user.id,
            project_id=project_id,
            include_shared=include_shared,
            skip=skip,
            limit=limit,
        )

        # Debug logging
        for req in requests:
            print(f"Request {req.id} shared_with: {req.shared_with}")

        response_data = [schemas.SimpleRequestOut.from_orm(request) for request in requests]
        return response_data
    except Exception as e:
        print(f"Error in get_requests: {str(e)}")
        raise


@router.get("/{request_id}", response_model=schemas.RequestOut)
def read_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific request."""
    request = crud_request.get_request_by_id(db=db, request_id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.user_id != current_user.id and not request.is_public:
        shares = crud_request.get_request_shares(db=db, request_id=request_id)
        if not any(share.shared_with_user_id == current_user.id for share in shares):
            raise HTTPException(status_code=403, detail="Not authorized to access this request")

    return request


@router.put("/{request_id}", response_model=schemas.RequestOut)
def update_request(
    request_id: int,
    request: schemas.RequestUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a request, ensuring only clients have update permissions."""
    if current_user.user_type != UserType.client:
        raise HTTPException(status_code=403, detail="Only clients can update requests")
    return crud_request.update_request(
        db=db, request_id=request_id, request_update=request, user_id=current_user.id
    )


@router.delete("/{request_id}", status_code=status.HTTP_200_OK)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a request, limited to the owner."""
    if current_user.user_type != UserType.client:
        raise HTTPException(status_code=403, detail="Only clients can delete requests")
    return crud_request.delete_request(db=db, request_id=request_id, user_id=current_user.id)


# ------------------ Sharing Functionality ------------------


@router.get("/{request_id}/shares/users", response_model=List[schemas.UserBasic])
def get_request_shares(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all users that a request is shared with."""
    request = crud_request.get_request_by_id(db=db, request_id=request_id)
    if not request or request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view shares")
    return crud_request.get_request_shares(db=db, request_id=request_id)


@router.post("/{request_id}/share", response_model=schemas.RequestShareResponse)
def share_request(
    request_id: int,
    share: schemas.RequestShare,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Share a request with another user."""
    if current_user.user_type != UserType.client:
        raise HTTPException(status_code=403, detail="Only clients can share requests")
    return crud_request.share_request(
        db=db, request_id=request_id, user_id=current_user.id, share=share
    )


@router.delete("/{request_id}/share/{user_id}", status_code=status.HTTP_200_OK)
def remove_share(
    request_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove request sharing for a specific user."""
    if current_user.user_type != UserType.client:
        raise HTTPException(status_code=403, detail="Only clients can modify request shares")
    return crud_request.remove_share(
        db=db, request_id=request_id, user_id=current_user.id, shared_user_id=user_id
    )


# ------------------ User Search ------------------


@router.get("/users/search", response_model=List[schemas.UserBasic])
def search_users(
    q: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Search users by username prefix."""
    if current_user.user_type == UserType.client:
        return crud_user.search_developers(db=db, username_prefix=q)
    else:
        return crud_user.search_clients(db=db, username_prefix=q)


@router.get("/search/users", response_model=List[schemas.UserBasic])
def search_users_alt(
    query: str,
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Alternative endpoint for user search (keeping for backward compatibility)."""
    if current_user.user_type == UserType.client:
        return crud_user.search_developers(db=db, username_prefix=query, limit=limit)
    else:
        return crud_user.search_clients(db=db, username_prefix=query, limit=limit)


# ------------------ Privacy Control ------------------


@router.put("/{request_id}/privacy", response_model=schemas.RequestOut)
def update_request_privacy(
    request_id: int,
    is_public: bool,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Toggle a request's public/private status."""
    if current_user.user_type != UserType.client:
        raise HTTPException(status_code=403, detail="Only clients can modify request privacy")
    return crud_request.toggle_request_privacy(
        db=db, request_id=request_id, user_id=current_user.id, is_public=is_public
    )
