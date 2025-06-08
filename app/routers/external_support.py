# app/routers/external_support.py

from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging
from datetime import datetime
import secrets
import string
from passlib.context import CryptContext

from .. import models, schemas, oauth2
from ..database import get_db

# Import your settings module
from ..config import settings

# Import your crud module
from .. import crud
from fastapi import Header

# Set up logging
logger = logging.getLogger(__name__)

# Set up password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define the router with the appropriate prefix
router = APIRouter(prefix="/api/external/support-tickets", tags=["External Support"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_external_support_ticket(
    ticket: schemas.ExternalSupportTicketCreate = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(oauth2.get_api_key),
):
    """
    Create a new support ticket from an external source (e.g., Analytics Hub)

    This endpoint is protected by an API key and creates a new support ticket
    in the ryze.ai system as a public request.
    """
    logger.info(
        f"Received external support ticket from {ticket.source} for {ticket.email}"
    )

    try:
        # Try to find the system service account
        system_user = (
            db.query(models.User).filter(models.User.email == "system@ryze.ai").first()
        )

        # If no system user exists, create one
        if not system_user:
            logger.info("System service account not found, creating one")

            # Generate a secure random password
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.choice(alphabet) for _ in range(24))

            # Hash the password
            hashed_password = pwd_context.hash(password)

            # Create the system user
            system_user = models.User(
                username="system",
                email="system@ryze.ai",
                full_name="ireallycode System",
                password=hashed_password,
                is_active=True,
                terms_accepted=True,
                user_type="developer",  # Set as developer to handle requests
            )

            # Add to database
            db.add(system_user)
            db.commit()
            db.refresh(system_user)
            logger.info(f"Created system service account with ID {system_user.id}")

        # Format the conversation history for human-readable display
        if ticket.conversation_history and isinstance(
            ticket.conversation_history, list
        ):
            conversation_formatted = "## CONVERSATION HISTORY:\n\n"
            for msg in ticket.conversation_history:
                timestamp = (
                    f" ({msg.timestamp})"
                    if hasattr(msg, "timestamp") and msg.timestamp
                    else ""
                )
                conversation_formatted += (
                    f"**{msg.role.upper()}**{timestamp}: {msg.content}\n\n"
                )
        else:
            conversation_formatted = "No conversation history provided"

        # Format the content to include the external support information
        content = f"""
## EXTERNAL SUPPORT TICKET

**Email**: {ticket.email}
**Source**: {ticket.source}
**Platform**: {ticket.platform or 'Not specified'}
**Website ID**: {ticket.website_id or 'Not specified'}

### ISSUE DESCRIPTION:
{ticket.issue}

{conversation_formatted}
"""

        # Create a new request object using your existing model
        new_request = models.Request(
            title=(
                f"Support: {ticket.issue[:50]}..."
                if len(ticket.issue) > 50
                else f"Support: {ticket.issue}"
            ),
            content=content,
            user_id=system_user.id,
            status="open",
            is_public=True,
            is_idea=False,
            seeks_collaboration=False,
            estimated_budget=None,
            # The important parts:
            request_metadata={
                "ticket_type": "external_support",
                "source": ticket.source,
                "email": ticket.email,
                "platform": ticket.platform,
                "website_id": ticket.website_id,
                "created_at": datetime.utcnow().isoformat(),
            },
            external_metadata={
                "source": ticket.source,
                "website_id": ticket.website_id,
                "email": ticket.email,
                "conversation": [
                    # Conversation history...
                ],
                "submitted_at": datetime.utcnow().isoformat(),
                "analytics_hub_id": ticket.analytics_hub_id,
            },
        )

        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        new_request.external_metadata["ryze_request_id"] = str(new_request.id)
        db.commit()  # Commit again to save the updated metadata

        logger.info(
            f"External support ticket created successfully with ID {new_request.id}"
        )

        # FIXED: Create conversation but don't auto-assign to anyone
        # Let developers see it and snag it manually like regular requests
        new_conversation = models.Conversation(
            request_id=new_request.id,
            starter_user_id=system_user.id,
            recipient_user_id=system_user.id,  # Keep as system user until manually snagged
            status="active",
            # Add these new fields for external support
            is_external=True,
            external_source=ticket.source,
            external_reference_id=str(ticket.analytics_hub_id),
            external_metadata={
                "email": ticket.email,
                "platform": ticket.platform,
                "website_id": ticket.website_id,
                "analytics_hub_id": ticket.analytics_hub_id,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        # Add an initial system message to the conversation
        initial_message = models.ConversationMessage(
            conversation_id=new_conversation.id,
            user_id=system_user.id,
            content=f"[EXTERNAL SUPPORT] Ticket created from {ticket.source} for {ticket.email}. Available for any developer to claim.",
        )
        db.add(initial_message)

        # Add the customer's message to the conversation
        customer_message = models.ConversationMessage(
            conversation_id=new_conversation.id,
            user_id=system_user.id,  # Using system user as proxy for external user
            content=ticket.issue,  # The actual content from the customer
            external_source=ticket.source,  # Mark as coming from external source
        )
        db.add(customer_message)
        db.commit()

        logger.info(f"Created external conversation with ID {new_conversation.id}")

        # REMOVED: Auto-assignment logic
        # External tickets should be available for any developer to snag manually
        # This ensures fair competition and prevents random assignment to inactive users
        logger.info(
            f"External ticket {new_request.id} created and ready for manual assignment"
        )

        # Return both the request and conversation IDs
        return {
            "status": "success",
            "message": "Support ticket created successfully",
            "ticket_id": new_request.id,
            "conversation_id": new_conversation.id,
        }
    except Exception as e:
        logger.error(f"Error creating external support ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create support ticket: {str(e)}",
        )


# For pre-flight CORS requests
@router.options("/", status_code=status.HTTP_204_NO_CONTENT)
def options_create_external_support_ticket():
    """
    Handle OPTIONS requests for CORS pre-flight check
    """


@router.post("/{ticket_id}/messages", status_code=201)
def add_external_message(
    ticket_id: int,
    message: schemas.ExternalMessageCreate,
    db: Session = Depends(get_db),
    api_key: str = Header(..., alias="X-API-Key"),
):
    # Validate API key
    if api_key != settings.EXTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Try to find the request by external reference ID in conversations first
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.external_reference_id == str(ticket_id))
        .filter(models.Conversation.is_external == True)
        .first()
    )

    # If not found by direct reference, look up by request ID
    if not conversation:
        # Get the request using the external metadata
        db_request = (
            db.query(models.Request)
            .filter(
                models.Request.external_metadata.has_key("analytics_hub_id"),
                models.Request.external_metadata["analytics_hub_id"].astext
                == str(ticket_id),
            )
            .first()
        )

        if not db_request:
            raise HTTPException(status_code=404, detail="Support ticket not found")

        # Now get the conversation for this request
        conversation = (
            db.query(models.Conversation)
            .filter(models.Conversation.request_id == db_request.id)
            .first()
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Get or create the system user for sending the message
    system_user = (
        db.query(models.User).filter(models.User.email == "system@ryze.ai").first()
    )

    if not system_user:
        raise HTTPException(status_code=500, detail="System user not found")

    # Create a new message in the conversation
    new_message = models.ConversationMessage(
        conversation_id=conversation.id,
        user_id=system_user.id,  # Use system user as proxy for external user
        content=message.content,
        external_source=conversation.external_source or "analytics-hub",
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {"id": new_message.id, "status": "created"}
