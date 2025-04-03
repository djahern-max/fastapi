from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import json
from datetime import datetime

from .. import models, schemas, oauth2
from ..database import get_db

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external/support-tickets", tags=["External Support"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_external_support_ticket(
    ticket: schemas.ExternalSupportTicketCreate,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(oauth2.verify_api_key),
):
    """
    Create a new support ticket from an external source (e.g., Analytics Hub)
    """
    logger.info(
        f"Received external support ticket from {ticket.source} for {ticket.email}"
    )

    try:
        # Get a system or support user to assign as the ticket owner
        # You can either use a dedicated support user or create one if needed
        support_user = (
            db.query(models.User).filter(models.User.email == "support@ryze.ai").first()
        )

        if not support_user:
            logger.warning("Support user not found, using the first admin user")
            # Fallback to an admin user if support user doesn't exist
            support_user = (
                db.query(models.User).filter(models.User.is_admin == True).first()
            )

        if not support_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No support or admin user found to own the ticket",
            )

        # Format the content to include the external support information
        content = f"""
EXTERNAL SUPPORT TICKET
-----------------------
Email: {ticket.email}
Source: {ticket.source}
Platform: {ticket.platform or 'Not specified'}
Website ID: {ticket.website_id or 'Not specified'}

ISSUE DESCRIPTION:
{ticket.issue}

CONVERSATION HISTORY:
{ticket.conversation_history or 'No conversation history provided'}
"""

        # Create a new request object using your existing model
        new_request = models.Request(
            title=(
                f"Support: {ticket.issue[:50]}..."
                if len(ticket.issue) > 50
                else f"Support: {ticket.issue}"
            ),
            content=content,
            user_id=support_user.id,
            status="open",  # Use your RequestStatus enum value
            is_public=False,
            contains_sensitive_data=True,  # Set to true for support tickets
            is_idea=False,
            seeks_collaboration=False,
            estimated_budget=None,  # No budget for support tickets
            # Store additional metadata that might be helpful
            request_metadata={
                "ticket_type": "external_support",
                "source": ticket.source,
                "email": ticket.email,
                "platform": ticket.platform,
                "website_id": ticket.website_id,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        logger.info(
            f"External support ticket created successfully with ID {new_request.id}"
        )

        # Optionally, create an initial conversation for this ticket
        try:
            new_conversation = models.Conversation(
                request_id=new_request.id,
                user_id=support_user.id,
                message=f"Support ticket created from {ticket.source} for {ticket.email}",
                is_system_message=True,
            )
            db.add(new_conversation)
            db.commit()
        except Exception as conv_error:
            logger.error(f"Error creating initial conversation: {str(conv_error)}")
            # Continue even if conversation creation fails

        return {
            "status": "success",
            "message": "Support ticket created successfully",
            "ticket_id": new_request.id,
        }
    except Exception as e:
        logger.error(f"Error creating external support ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create support ticket: {str(e)}",
        )
