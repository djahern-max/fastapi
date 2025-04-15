# New file: app/routers/playlists.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import schemas, models, oauth2
from ..database import get_db
from ..crud import crud_playlist
from datetime import datetime

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("/", response_model=schemas.PlaylistResponse)
def create_playlist(
    playlist: schemas.PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return crud_playlist.create_playlist(db, playlist, current_user.id)


@router.get("/{playlist_id}", response_model=schemas.PlaylistDetail)
def get_playlist(playlist_id: int, db: Session = Depends(get_db)):
    playlist = crud_playlist.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found"
        )
    return playlist


@router.get("/user/{user_id}", response_model=List[schemas.PlaylistResponse])
def get_user_playlists(
    user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud_playlist.get_playlists_by_user(db, user_id, skip, limit)


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
