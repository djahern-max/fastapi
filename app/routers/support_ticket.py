# app/routers/support_ticket.py
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from .. import models, schemas, crud
from ..database import get_db
from ..oauth2 import get_current_user
import logging
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support/tickets", tags=["Support"])


@router.post("/{ticket_id}/messages", status_code=201)
async def add_ticket_message(
    ticket_id: str,
    message: schemas.TicketMessageCreate = Body(...),
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Add a message to a support ticket from ireallycode.COM
    """
    # Validate API key if present (for system-to-system communication)
    if api_key:
        if api_key != settings.RYZE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Find the conversation in Analytics Hub
        conversation = crud.get_conversation_by_ryze_ticket_id(db, ticket_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Create a new message
        new_message = crud.create_assistant_message(
            db,
            conversation_id=conversation.id,
            role="system" if message.sender_type == "support" else "user",
            content=message.content,
            message_metadata={
                "source": "ryze",
                "original_id": message.message_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return {"id": new_message.id, "status": "created"}
    else:
        # User-initiated message (requires authentication)
        current_user = Depends(get_current_user)

        # Logic for user-initiated messages
        # [Implementation goes here]

        raise HTTPException(status_code=501, detail="Not implemented")
