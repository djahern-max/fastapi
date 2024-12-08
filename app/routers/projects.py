from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..oauth2 import get_current_user
from app import schemas, crud, models
from fastapi import status
from fastapi.params import Query

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=schemas.ProjectOut)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # User type check is now handled in the crud function
    return crud.crud_project.create_project(db=db, project=project, user_id=current_user.id)


@router.get("/", response_model=list[schemas.ProjectOut])
def get_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    include_stats: bool = Query(False),
):
    """Get all projects with optional stats about their requests."""
    projects = crud.crud_project.get_projects_by_user(db=db, user_id=current_user.id)
    if include_stats:
        for project in projects:
            project.stats = crud.crud_project.get_project_stats(db=db, project_id=project.id)
    return projects


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify user is a client before allowing deletion
    if current_user.user_type != models.UserType.client:  # Using lowercase
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can delete projects"
        )

    crud.crud_project.delete_project(db=db, project_id=project_id, user_id=current_user.id)
    return {"message": "Project deleted successfully"}


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # First get the project
    project = crud.crud_project.get_project(db=db, project_id=project_id)

    # Check if user owns the project or has access
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project"
        )

    return project
