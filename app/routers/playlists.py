# New file: app/routers/playlists.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import schemas, models, oauth2
from ..database import get_db
from ..crud import crud_playlist
from datetime import datetime
from ..schemas import PlaylistResponse, PlaylistDetail
import uuid

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("/", response_model=schemas.PlaylistResponse)
def create_playlist(
    playlist: schemas.PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return crud_playlist.create_playlist(db, playlist, current_user.id)


@router.get("/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(playlist_id: int, db: Session = Depends(get_db)):
    # Get the playlist with eager loading of videos
    playlist = (
        db.query(models.VideoPlaylist)
        .filter(models.VideoPlaylist.id == playlist_id)
        .first()
    )

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Count the videos explicitly
    video_count = (
        db.query(models.PlaylistVideo)
        .filter(models.PlaylistVideo.playlist_id == playlist_id)
        .count()
    )

    # Fetch the videos associated with this playlist
    playlist_videos = (
        db.query(models.PlaylistVideo, models.Video)
        .join(models.Video, models.PlaylistVideo.video_id == models.Video.id)
        .filter(models.PlaylistVideo.playlist_id == playlist_id)
        .order_by(models.PlaylistVideo.order)
        .all()
    )

    # Format the videos with their playlist order
    videos = []
    for pv, video in playlist_videos:
        video_dict = {**video.__dict__}
        video_dict["order"] = pv.order
        videos.append(video_dict)

    # Prepare the response
    playlist_data = {**playlist.__dict__}
    playlist_data["videos"] = videos
    playlist_data["video_count"] = video_count  # Add explicit count

    return playlist_data


@router.get("/user/{user_id}", response_model=List[PlaylistResponse])
def get_user_playlists(user_id: int, db: Session = Depends(get_db)):
    # Get all playlists for this user
    playlists = (
        db.query(models.VideoPlaylist)
        .filter(models.VideoPlaylist.creator_id == user_id)
        .all()
    )

    # Create a list to store the enhanced playlists with counts
    enhanced_playlists = []

    # Process each playlist
    for playlist in playlists:
        # Convert to dict for easier manipulation
        playlist_dict = playlist.__dict__.copy()

        # Count videos in this playlist
        video_count = (
            db.query(models.PlaylistVideo)
            .filter(models.PlaylistVideo.playlist_id == playlist.id)
            .count()
        )

        # Add the count explicitly
        playlist_dict["video_count"] = video_count

        # Add to our enhanced list
        enhanced_playlists.append(playlist_dict)

    return enhanced_playlists


@router.post("/{playlist_id}/videos/{video_id}")
def add_video_to_playlist(
    playlist_id: int,
    video_id: int,
    order: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    print(f"Adding video {video_id} to playlist {playlist_id}")
    # Print relevant info for debugging
    print(f"User: {current_user.id}, Order: {order}")

    try:
        # Verify ownership or permissions
        playlist = crud_playlist.get_playlist(db, playlist_id)
        print(f"Playlist found: {playlist is not None}")

        # Check the type of playlist
        print(f"Playlist type: {type(playlist)}")

        # Fixed: Check if it's a dictionary and access accordingly
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found",
            )

        # Check if it's a dictionary (ORM object would be true here)
        if isinstance(playlist, dict):
            creator_id = playlist.get("creator_id")
        else:
            # It's an ORM object, use attribute access
            creator_id = playlist.creator_id

        if creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this playlist",
            )

        result = crud_playlist.add_video_to_playlist(db, playlist_id, video_id, order)
        print(f"Add video result: {result}")
        return result
    except Exception as e:
        print(f"ERROR in add_video_to_playlist: {str(e)}")
        print(f"Exception type: {type(e)}")
        # Let's see the full error traceback
        import traceback

        print(traceback.format_exc())
        # After printing, re-raise to preserve the 500 error
        raise


@router.put("/{playlist_id}", response_model=schemas.PlaylistResponse)
def update_playlist(
    playlist_id: int,
    playlist_update: schemas.PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Get the playlist
    playlist_query = db.query(models.VideoPlaylist).filter(
        models.VideoPlaylist.id == playlist_id
    )
    playlist = playlist_query.first()

    # Check if playlist exists
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist with id {playlist_id} not found",
        )

    # Check if user owns the playlist
    if playlist.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this playlist",
        )

    # Update the playlist with the new data
    for key, value in playlist_update.dict(exclude_unset=True).items():
        setattr(playlist, key, value)

    # Commit changes to database
    db.commit()
    db.refresh(playlist)

    return playlist


@router.get("/video/{video_id}", response_model=List[PlaylistResponse])
def get_video_playlists(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(
        oauth2.get_current_active_user_optional
    ),
):
    """Get all playlists containing a specific video"""
    # First check if the video exists
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get the video owner
    video_owner_id = video.user_id

    # Get playlists that contain this video
    playlist_videos = (
        db.query(models.PlaylistVideo)
        .filter(models.PlaylistVideo.video_id == video_id)
        .all()
    )

    playlist_ids = [pv.playlist_id for pv in playlist_videos]

    if not playlist_ids:
        return []

    # Query the playlists
    playlists_query = db.query(models.VideoPlaylist).filter(
        models.VideoPlaylist.id.in_(playlist_ids)
    )

    # If the current user is not the video owner, only show public playlists
    if not current_user or current_user.id != video_owner_id:
        playlists_query = playlists_query.filter(models.VideoPlaylist.is_public == True)

    playlists = playlists_query.all()

    # Add video count to each playlist
    enhanced_playlists = []
    for playlist in playlists:
        playlist_dict = playlist.__dict__.copy()
        video_count = (
            db.query(models.PlaylistVideo)
            .filter(models.PlaylistVideo.playlist_id == playlist.id)
            .count()
        )
        playlist_dict["video_count"] = video_count
        enhanced_playlists.append(playlist_dict)

    return enhanced_playlists


# Remove the duplicate route and update the implementation
@router.post("/{playlist_id}/share", response_model=dict)
def generate_share_link(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    """Generate a shareable link for a playlist"""
    # Get the playlist
    playlist = (
        db.query(models.VideoPlaylist)
        .filter(models.VideoPlaylist.id == playlist_id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Check if user owns the playlist
    if playlist.creator_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the playlist owner can generate share links"
        )

    # Generate share token if it doesn't exist
    if not playlist.share_token:
        playlist.share_token = str(uuid.uuid4())
        db.commit()
        db.refresh(playlist)  # Refresh to ensure we have the updated playlist

    # Return token - frontend can construct full URL if needed
    return {"share_token": playlist.share_token}


@router.get("/shared/{share_token}")
def get_shared_playlist(share_token: str, db: Session = Depends(get_db)):
    """Get a playlist by its share token"""
    # Find the playlist with the given share token
    playlist = (
        db.query(models.VideoPlaylist)
        .filter(models.VideoPlaylist.share_token == share_token)
        .first()
    )

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shared playlist not found"
        )

    # Get the videos in this playlist with their order
    playlist_videos = (
        db.query(models.PlaylistVideo, models.Video)
        .join(models.Video, models.PlaylistVideo.video_id == models.Video.id)
        .filter(models.PlaylistVideo.playlist_id == playlist.id)
        .order_by(models.PlaylistVideo.order)
        .all()
    )

    # Format the response
    videos = []
    for pv, video in playlist_videos:
        video_dict = {**video.__dict__}
        video_dict["order"] = pv.order
        videos.append(video_dict)

    # Create the response with the playlist and its videos
    playlist_data = {**playlist.__dict__}
    playlist_data["videos"] = videos

    return playlist_data


@router.get("/", response_model=List[schemas.PlaylistResponse])
def get_public_playlists(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user_optional),
):
    """
    Get all public playlists.
    If user is authenticated, also include their private playlists.
    """
    # Base query for public playlists
    query = db.query(models.VideoPlaylist).filter(
        models.VideoPlaylist.is_public == True
    )

    # If user is authenticated, include their private playlists too
    if current_user:
        query = db.query(models.VideoPlaylist).filter(
            (models.VideoPlaylist.is_public == True)
            | (models.VideoPlaylist.creator_id == current_user.id)
        )

    playlists = query.all()
    return playlists
