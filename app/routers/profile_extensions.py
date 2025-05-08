from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database, oauth2
from ..database import get_db
import logging
from datetime import datetime

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile/developer", tags=["Profile Extensions"])


# Work Experience Endpoints
@router.post(
    "/work-experience",
    response_model=schemas.WorkExperienceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_work_experience(
    work_exp: schemas.WorkExperienceCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new work experience entry for the developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can add work experience",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer profile not found. Please create a profile first.",
        )

    # Create the work experience
    work_experience = models.WorkExperience(
        developer_id=developer_profile.id, **work_exp.dict()
    )

    db.add(work_experience)
    db.commit()
    db.refresh(work_experience)

    return work_experience


@router.get("/work-experience", response_model=List[schemas.WorkExperienceOut])
def get_work_experience(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get all work experience entries for the developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can view their work experience",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    # Get all work experiences
    work_experiences = (
        db.query(models.WorkExperience)
        .filter(models.WorkExperience.developer_id == developer_profile.id)
        .all()
    )

    return work_experiences


@router.put("/work-experience/{work_exp_id}", response_model=schemas.WorkExperienceOut)
def update_work_experience(
    work_exp_id: int,
    work_exp_update: schemas.WorkExperienceUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update a work experience entry"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can update work experience",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    # Get the work experience
    work_experience = (
        db.query(models.WorkExperience)
        .filter(
            models.WorkExperience.id == work_exp_id,
            models.WorkExperience.developer_id == developer_profile.id,
        )
        .first()
    )

    if not work_experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work experience not found"
        )

    # Update the work experience
    update_data = work_exp_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(work_experience, key, value)

    db.commit()
    db.refresh(work_experience)

    return work_experience


@router.delete("/work-experience/{work_exp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_experience(
    work_exp_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a work experience entry"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can delete work experience",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    # Get the work experience
    work_experience = (
        db.query(models.WorkExperience)
        .filter(
            models.WorkExperience.id == work_exp_id,
            models.WorkExperience.developer_id == developer_profile.id,
        )
        .first()
    )

    if not work_experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work experience not found"
        )

    # Delete the work experience
    db.delete(work_experience)
    db.commit()

    return None


# Education Endpoints
@router.post(
    "/education",
    response_model=schemas.EducationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_education(
    education: schemas.EducationCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new education entry for the developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can add education",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer profile not found. Please create a profile first.",
        )

    # Create the education
    education_entry = models.Education(
        developer_id=developer_profile.id, **education.dict()
    )

    db.add(education_entry)
    db.commit()
    db.refresh(education_entry)

    return education_entry


@router.get("/education", response_model=List[schemas.EducationOut])
def get_education(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get all education entries for the developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can view their education",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    # Get all education entries
    education_entries = (
        db.query(models.Education)
        .filter(models.Education.developer_id == developer_profile.id)
        .all()
    )

    return education_entries


@router.put("/education/{education_id}", response_model=schemas.EducationOut)
def update_education(
    education_id: int,
    education_update: schemas.EducationUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update an education entry"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can update education",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    # Get the education entry
    education_entry = (
        db.query(models.Education)
        .filter(
            models.Education.id == education_id,
            models.Education.developer_id == developer_profile.id,
        )
        .first()
    )

    if not education_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Education entry not found"
        )

    # Update the education entry
    update_data = education_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(education_entry, key, value)

    db.commit()
    db.refresh(education_entry)

    return education_entry


@router.delete("/education/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    education_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete an education entry"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can delete education",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Developer profile not found"
        )

    # Get the education entry
    education_entry = (
        db.query(models.Education)
        .filter(
            models.Education.id == education_id,
            models.Education.developer_id == developer_profile.id,
        )
        .first()
    )

    if not education_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Education entry not found"
        )

    # Delete the education entry
    db.delete(education_entry)
    db.commit()

    return None


# Certification Endpoints
@router.post(
    "/certification",
    response_model=schemas.CertificationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_certification(
    certification: schemas.CertificationCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new certification for the developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can add certifications",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer profile not found. Please create a profile first.",
        )

    # Create the certification
    certification_entry = models.Certification(
        developer_id=developer_profile.id, **certification.dict()
    )

    db.add(certification_entry)
    db.commit()
    db.refresh(certification_entry)

    return certification_entry


@router.get("/certification", response_model=List[schemas.CertificationOut])
def get_certifications(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get all certifications for the developer profile"""
    # [Similar implementation as above]


@router.put("/certification/{cert_id}", response_model=schemas.CertificationOut)
def update_certification(
    cert_id: int,
    certification_update: schemas.CertificationUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update a certification"""
    # [Similar implementation as above]


@router.delete("/certification/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certification(
    cert_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a certification"""
    # [Similar implementation as above]


# Portfolio Item Endpoints
@router.post(
    "/portfolio",
    response_model=schemas.PortfolioItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio_item(
    portfolio_item: schemas.PortfolioItemCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new portfolio item for the developer profile"""
    if current_user.user_type != models.UserType.developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can add portfolio items",
        )

    # Get the developer profile
    developer_profile = (
        db.query(models.DeveloperProfile)
        .filter(models.DeveloperProfile.user_id == current_user.id)
        .first()
    )

    if not developer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer profile not found. Please create a profile first.",
        )

    # Create the portfolio item
    portfolio_entry = models.PortfolioItem(
        developer_id=developer_profile.id, **portfolio_item.dict()
    )

    db.add(portfolio_entry)
    db.commit()
    db.refresh(portfolio_entry)

    return portfolio_entry


@router.get("/portfolio", response_model=List[schemas.PortfolioItemOut])
def get_portfolio_items(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get all portfolio items for the developer profile"""
    # [Similar implementation as above]


@router.put("/portfolio/{portfolio_id}", response_model=schemas.PortfolioItemOut)
def update_portfolio_item(
    portfolio_id: int,
    portfolio_update: schemas.PortfolioItemUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update a portfolio item"""
    # [Similar implementation as above]


@router.delete("/portfolio/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_item(
    portfolio_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a portfolio item"""
    # [Similar implementation as above]
