# app/utils/external_service.py

import httpx
import os
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


async def send_message_to_analytics_hub(
    db: Session,
    message_id: int,
    content: str,
    conversation_id: Optional[int] = None,
    request_id: Optional[int] = None,
    external_reference_id: Optional[str] = None,
    external_source: Optional[str] = "analytics-hub",
) -> bool:
    """
    Send a message from ireallycode.com to Analytics Hub

    Args:
        db: Database session
        message_id: The message ID
        content: The message content
        conversation_id: The conversation ID (preferred way to identify)
        request_id: The request ID (fallback)
        external_reference_id: Direct reference to Analytics Hub ID (most reliable)
        external_source: Source system identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from .. import models
        from ..config import settings

        # Log start of operation
        logger.info(
            f"Sending message to Analytics Hub: msg_id={message_id}, conv_id={conversation_id}, req_id={request_id}"
        )

        # Get message and confirm it exists
        message = (
            db.query(models.ConversationMessage)
            .filter(models.ConversationMessage.id == message_id)
            .first()
        )
        if not message:
            logger.error(f"Message {message_id} not found")
            return False

        # Get the user who sent the message
        user = db.query(models.User).filter(models.User.id == message.user_id).first()
        if not user:
            logger.error(f"User for message {message_id} not found")
            return False

        # Get conversation if not provided
        conversation = None
        analytics_hub_id = external_reference_id  # Use direct reference if provided

        # Try to get conversation by ID
        if conversation_id:
            conversation = (
                db.query(models.Conversation)
                .filter(models.Conversation.id == conversation_id)
                .first()
            )
        elif message.conversation_id:
            conversation = (
                db.query(models.Conversation)
                .filter(models.Conversation.id == message.conversation_id)
                .first()
            )

        # Use conversation external reference if available
        if (
            conversation
            and hasattr(conversation, "external_reference_id")
            and conversation.external_reference_id
        ):
            analytics_hub_id = conversation.external_reference_id
            logger.info(
                f"Using external_reference_id from conversation: {analytics_hub_id}"
            )

        # If no direct reference, try to get request
        if not analytics_hub_id:
            req = None

            # Get request from conversation
            if conversation:
                req = (
                    db.query(models.Request)
                    .filter(models.Request.id == conversation.request_id)
                    .first()
                )
            # Or get request directly if provided
            elif request_id:
                req = (
                    db.query(models.Request)
                    .filter(models.Request.id == request_id)
                    .first()
                )

            # Extract analytics_hub_id from request metadata
            if (
                req
                and req.external_metadata
                and isinstance(req.external_metadata, dict)
            ):
                analytics_hub_id = req.external_metadata.get("analytics_hub_id")
                logger.info(
                    f"Using analytics_hub_id from request metadata: {analytics_hub_id}"
                )

        # If we still don't have an ID, we can't proceed
        if not analytics_hub_id:
            logger.error("Could not find analytics_hub_id from any source")
            return False

        # Prepare the webhook payload
        payload = {
            "analytics_hub_id": analytics_hub_id,
            "content": content,
            "sender_type": "developer",
            "sender": user.username,
            "sender_id": user.id,
            "message_id": str(message.id),
            "external_ticket_id": (
                conversation.request_id if conversation else request_id
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Get API endpoint and key from settings
        api_url = settings.ANALYTICS_HUB_API_URL
        if not api_url:
            logger.error("ANALYTICS_HUB_API_URL setting not configured")
            return False

        webhook_url = f"{api_url}/ryze/messages"
        api_key = settings.ANALYTICS_HUB_API_KEY

        if not api_key:
            logger.error("ANALYTICS_HUB_API_KEY setting not configured")
            return False

        # Set up headers
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

        # Log the request details
        logger.info(f"Sending webhook to: {webhook_url}")
        logger.debug(f"Payload: {payload}")

        # Make the request
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload, headers=headers)

            if response.status_code in (200, 201, 204):
                logger.info(
                    f"Successfully sent message to Analytics Hub. Response: {response.status_code}"
                )

                # Update conversation's last sync time if available
                if conversation and hasattr(conversation, "external_metadata"):
                    if not conversation.external_metadata:
                        conversation.external_metadata = {}
                    conversation.external_metadata["last_synced_at"] = (
                        datetime.utcnow().isoformat()
                    )
                    db.commit()

                return True
            else:
                logger.error(
                    f"Failed to send message to Analytics Hub. Status: {response.status_code}, Response: {response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"Exception sending message to Analytics Hub: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return False
