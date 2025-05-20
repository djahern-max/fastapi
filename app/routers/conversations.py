# app/routers/conversations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any
from .. import models, schemas, database, oauth2
from sqlalchemy import or_
from ..middleware import require_active_subscription
from ..database import get_db
from fastapi import status
from sqlalchemy.sql import func
from typing import Dict
from ..utils import external_service
from .analyticshub_webhook import send_message_webhook

import logging

# Get the logger at the top of your file, outside any function
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/conversations", tags=["Conversations"])


# In routers/conversations.py


@router.post("/", response_model=schemas.ConversationOut)
def create_conversation(
    conversation: schemas.ConversationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_active_subscription),
):
    # Get the request and its owner
    request = (
        db.query(models.Request)
        .join(models.User)
        .filter(models.Request.id == conversation.request_id)
        .first()
    )

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check if this is an external support ticket
    is_external_support = False
    if hasattr(request, "request_metadata") and request.request_metadata:
        if (
            isinstance(request.request_metadata, dict)
            and request.request_metadata.get("ticket_type") == "external_support"
        ):
            is_external_support = True

    # For external tickets, check if there's already an external conversation
    if is_external_support:
        existing_external_conv = (
            db.query(models.Conversation)
            .filter(
                models.Conversation.request_id == conversation.request_id,
                models.Conversation.is_external == True,
                models.Conversation.external_source == "analytics-hub",
            )
            .first()
        )

        if existing_external_conv:
            # Return the existing conversation instead of creating a new one
            return existing_external_conv

    # Create new conversation
    new_conversation = models.Conversation(
        request_id=conversation.request_id,
        starter_user_id=current_user.id,
        recipient_user_id=request.user_id,
        status="active",
        is_external=is_external_support,  # Set this flag based on ticket type
        external_source="analytics-hub" if is_external_support else None,
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    return new_conversation


from .analyticshub_webhook import send_message_webhook


@router.post("/{id}/messages", response_model=schemas.ConversationMessageOut)
async def create_message(  # Make this async
    id: int,
    message: schemas.ConversationMessageCreate,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    try:
        print(
            f"Creating message with video_ids: {message.video_ids} and include_profile: {message.include_profile}"
        )

        # Check if conversation exists
        conversation = (
            db.query(models.Conversation).filter(models.Conversation.id == id).first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check if this is an external conversation
        is_external = getattr(conversation, "is_external", False)

        # Authorization check - handle differently for external conversations
        if is_external:
            # For external support conversations, allow system user and assigned developers
            request = (
                db.query(models.Request)
                .filter(models.Request.id == conversation.request_id)
                .first()
            )
            if not request:
                raise HTTPException(status_code=404, detail="Related request not found")

            is_system = current_user.email == "system@ireallycode.com"

            is_assigned = (
                db.query(models.SnaggedRequest)
                .filter(
                    models.SnaggedRequest.request_id == conversation.request_id,
                    models.SnaggedRequest.developer_id == current_user.id,
                    models.SnaggedRequest.is_active == True,
                )
                .first()
                is not None
            )

            if not (is_system or is_assigned):
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to post in this external support conversation",
                )
        else:
            if current_user.id not in [
                conversation.starter_user_id,
                conversation.recipient_user_id,
            ]:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to post in this conversation",
                )

        # Create the new message
        new_message = models.ConversationMessage(
            conversation_id=id, user_id=current_user.id, content=message.content
        )
        db.add(new_message)
        db.flush()

        linked_content = []

        # Handle video links
        if message.video_ids:
            videos = (
                db.query(models.Video)
                .filter(
                    models.Video.id.in_(message.video_ids),
                    models.Video.user_id == current_user.id,
                )
                .all()
            )

            if len(videos) != len(message.video_ids):
                raise HTTPException(
                    status_code=400,
                    detail="One or more videos not found or not owned by user",
                )

            for video in videos:
                content_link = models.ConversationContentLink(
                    conversation_id=id,
                    message_id=new_message.id,
                    content_type="video",
                    content_id=video.id,
                    title=video.title,
                    url=video.file_path,
                )
                db.add(content_link)
                linked_content.append(
                    {
                        "id": video.id,
                        "type": "video",
                        "content_id": video.id,
                        "title": video.title,
                        "url": video.file_path,
                    }
                )

        # Handle profile link
        if message.include_profile:
            print("Adding profile link")
            profile_link = models.ConversationContentLink(
                conversation_id=id,
                message_id=new_message.id,
                content_type="profile",
                content_id=current_user.id,
                title=current_user.username,
                url=f"/profile/developer/{current_user.id}",
            )
            db.add(profile_link)
            linked_content.append(
                {
                    "id": current_user.id,
                    "type": "profile",
                    "content_id": current_user.id,
                    "title": current_user.username,
                    "url": f"/profile/developer/{current_user.id}",
                }
            )

        db.commit()
        db.refresh(new_message)

        content_links = (
            db.query(models.ConversationContentLink)
            .filter(models.ConversationContentLink.message_id == new_message.id)
            .all()
        )

        for i, link in enumerate(content_links):
            if i < len(linked_content):
                linked_content[i]["id"] = link.id

        response = {
            "id": new_message.id,
            "conversation_id": new_message.conversation_id,
            "user_id": new_message.user_id,
            "content": new_message.content,
            "created_at": new_message.created_at,
            "linked_content": linked_content,
        }

        external_reference_id = None

        # Handle external support ticket message forwarding
        if is_external:
            external_reference_id = getattr(conversation, "external_reference_id", None)

            if not external_reference_id and conversation.request_id:
                request = (
                    db.query(models.Request)
                    .filter(models.Request.id == conversation.request_id)
                    .first()
                )
                if (
                    request
                    and request.external_metadata
                    and "analytics_hub_id" in request.external_metadata
                ):
                    external_reference_id = request.external_metadata[
                        "analytics_hub_id"
                    ]

        if external_reference_id:
            print(
                f"Sending message to external system with ID: {external_reference_id}"
            )
            from ..utils.external_service import send_message_to_analytics_hub

            # Use await directly
            await send_message_to_analytics_hub(
                db=db,
                conversation_id=conversation.id,
                message_id=new_message.id,
                content=new_message.content,
                external_reference_id=external_reference_id,
                external_source=getattr(
                    conversation, "external_source", "analytics-hub"
                ),
            )
            print("Message sent to Analytics Hub successfully")

        # For webhook call
        if (
            conversation
            and conversation.is_external
            and conversation.external_source == "analytics-hub"
            and conversation.external_reference_id
        ):
            # If this is a sync function, no need to await
            # If it's async, you need to await it
            send_message_webhook(
                ticket_id=conversation.external_reference_id,
                message_content=message.content,
                message_id=f"ryze-msg-{new_message.id}",
                sender_type="support",
                sender_name=current_user.username,
                sender_id=str(current_user.id),
            )

        return response

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"Error creating message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/user/list", response_model=List[schemas.ConversationWithMessages])
def list_user_conversations(
    request_id: int = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = db.query(models.Conversation).filter(
        or_(
            models.Conversation.starter_user_id == current_user.id,
            models.Conversation.recipient_user_id == current_user.id,
        )
    )

    if request_id:
        query = query.filter(models.Conversation.request_id == request_id)

    conversations = query.order_by(models.Conversation.created_at.desc()).all()

    result = []
    for conv in conversations:
        request = (
            db.query(models.Request)
            .filter(models.Request.id == conv.request_id)
            .first()
        )

        # Initialize messages array for this conversation
        messages = []

        # Fetch all messages for this conversation
        conversation_messages = (
            db.query(models.ConversationMessage)
            .filter(models.ConversationMessage.conversation_id == conv.id)
            .all()
        )

        # Process each message
        for msg in conversation_messages:
            # First, get content links
            content_links = (
                db.query(models.ConversationContentLink)
                .filter(models.ConversationContentLink.message_id == msg.id)
                .all()
            )

            # Build linked_content array
            linked_content = []
            for link in content_links:
                if link.content_type == "video":
                    video = (
                        db.query(models.Video)
                        .filter(models.Video.id == link.content_id)
                        .first()
                    )
                    if video:
                        linked_content.append(
                            {
                                "id": link.id,
                                "type": "video",
                                "content_id": video.id,
                                "title": video.title,
                                "url": video.file_path,
                            }
                        )
                elif link.content_type == "profile":
                    user = (
                        db.query(models.User)
                        .filter(models.User.id == link.content_id)
                        .first()
                    )
                    if user:
                        linked_content.append(
                            {
                                "id": link.id,
                                "type": "profile",
                                "content_id": user.id,
                                "title": f"{user.username}'s Profile",
                                "url": f"/profile/developer/{user.id}",
                            }
                        )

            # Check if message is external
            is_external = (
                hasattr(msg, "external_source")
                and msg.external_source == "analytics-hub"
            )

            # Now build the complete message object
            message_data = {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "user_id": msg.user_id,
                "content": msg.content,
                "created_at": msg.created_at,
                "is_external": is_external,
                "sender_type": (
                    "external_user"
                    if is_external
                    else "system" if msg.user_id == request.user_id else "developer"
                ),
                "linked_content": linked_content,
            }
            messages.append(message_data)

        # Finish building the conversation data
        starter = (
            db.query(models.User).filter(models.User.id == conv.starter_user_id).first()
        )
        recipient = (
            db.query(models.User)
            .filter(models.User.id == conv.recipient_user_id)
            .first()
        )

        conv_data = {
            "id": conv.id,
            "request_id": conv.request_id,
            "starter_user_id": conv.starter_user_id,
            "recipient_user_id": conv.recipient_user_id,
            "starter_username": starter.username if starter else "Unknown",
            "recipient_username": recipient.username if recipient else "Unknown",
            "status": conv.status,
            "created_at": conv.created_at,
            "messages": messages,
            "request_title": request.title if request else "Unknown Request",
        }
        result.append(conv_data)

    return result


@router.get("/request/conversation-counts", response_model=Dict[int, int])
def get_conversation_counts(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Query to get counts of conversations grouped by request_id
    conversation_counts = (
        db.query(
            models.Conversation.request_id,
            func.count(models.Conversation.id).label("count"),
        )
        .group_by(models.Conversation.request_id)
        .all()
    )

    # Convert to dictionary format {request_id: count}
    result = {conv.request_id: conv.count for conv in conversation_counts}

    return result


@router.get(
    "/{conversation_id}/messages", response_model=List[schemas.ConversationMessageOut]
)
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Check if conversation exists and user has access
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if current_user.id not in [
        conversation.starter_user_id,
        conversation.recipient_user_id,
    ]:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this conversation"
        )

    # Get messages for this conversation
    messages = (
        db.query(models.ConversationMessage)
        .filter(models.ConversationMessage.conversation_id == conversation_id)
        .order_by(models.ConversationMessage.created_at)
        .all()
    )

    result = []
    for msg in messages:
        content_links = (
            db.query(models.ConversationContentLink)
            .filter(models.ConversationContentLink.message_id == msg.id)
            .all()
        )

        linked_content = []
        for link in content_links:
            if link.content_type == "video":
                video = (
                    db.query(models.Video)
                    .filter(models.Video.id == link.content_id)
                    .first()
                )
                if video:
                    linked_content.append(
                        {
                            "id": link.id,
                            "type": "video",
                            "content_id": video.id,
                            "title": video.title,
                            "url": video.file_path,
                        }
                    )
            elif link.content_type == "profile":
                user = (
                    db.query(models.User)
                    .filter(models.User.id == link.content_id)
                    .first()
                )
                if user:
                    linked_content.append(
                        {
                            "id": link.id,
                            "type": "profile",
                            "content_id": user.id,
                            "title": f"{user.username}'s Profile",
                            "url": f"/profile/developer/{user.id}",
                        }
                    )

        result.append(
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "user_id": msg.user_id,
                "content": msg.content,
                "created_at": msg.created_at,
                "linked_content": linked_content,
            }
        )

    return result


@router.patch("/{id}", response_model=schemas.ConversationOut)
def update_conversation(
    id: int,
    conversation_update: schemas.ConversationUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Query for the conversation
    conversation = (
        db.query(models.Conversation).filter(models.Conversation.id == id).first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if user is part of the conversation
    if current_user.id not in [
        conversation.starter_user_id,
        conversation.recipient_user_id,
    ]:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this conversation"
        )

    # Update the conversation status
    conversation.status = conversation_update.status

    db.commit()
    db.refresh(conversation)

    return conversation


@router.post("/from-video/", response_model=schemas.ConversationOut)
def create_conversation_from_video(
    conversation_data: schemas.ConversationFromVideo,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Get the video and its owner
    video = (
        db.query(models.Video)
        .filter(models.Video.id == conversation_data.video_id)
        .first()
    )

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify the current user is a client
    if current_user.user_type != models.UserType.client:
        raise HTTPException(
            status_code=403, detail="Only clients can initiate video conversations"
        )

    # Create a request for this video conversation
    request = models.Request(
        title=conversation_data.title,
        content=conversation_data.content,
        user_id=current_user.id,
        is_public=True,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    # Create the conversation
    new_conversation = models.Conversation(
        request_id=request.id,
        starter_user_id=current_user.id,
        recipient_user_id=video.user_id,
        status="active",
    )

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    return new_conversation


@router.get("/{conversation_id}", response_model=schemas.ConversationWithMessages)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Get the conversation with all relationships loaded
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is an external conversation
    is_external = getattr(conversation, "is_external", False)

    # Authorization check - handle differently for external conversations
    if is_external:
        # For external support conversations, allow system user and assigned developers
        request = (
            db.query(models.Request)
            .filter(models.Request.id == conversation.request_id)
            .first()
        )
        if not request:
            raise HTTPException(status_code=404, detail="Related request not found")

        is_system = current_user.email == "system@ireallycode.com"

        is_assigned = (
            db.query(models.SnaggedRequest)
            .filter(
                models.SnaggedRequest.request_id == conversation.request_id,
                models.SnaggedRequest.developer_id == current_user.id,
                models.SnaggedRequest.is_active == True,
            )
            .first()
            is not None
        )

        if not (is_system or is_assigned):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this external support conversation",
            )
    else:
        # Standard permission check for non-external conversations
        if (
            conversation.starter_user_id != current_user.id
            and conversation.recipient_user_id != current_user.id
        ):
            raise HTTPException(
                status_code=403, detail="Not authorized to view this conversation"
            )

    # Create a dictionary with all the required fields for the response schema
    response_data = {
        "id": conversation.id,
        "request_id": conversation.request_id,
        "starter_user_id": conversation.starter_user_id,
        "recipient_user_id": conversation.recipient_user_id,
        "status": conversation.status,
        "agreed_amount": None,  # Replace with actual value if it exists
        "created_at": conversation.created_at,
        # Get these values from the relationships
        "starter_username": conversation.starter.username,
        "recipient_username": conversation.recipient.username,
        "request_title": conversation.request.title,
        # Get messages
        "messages": conversation.messages,
    }

    # Return the constructed response
    return response_data


# In app/routers/conversations.py
@router.post(
    "/{conversation_id}/messages/{message_id}/transmit", response_model=Dict[str, Any]
)
async def transmit_message(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    """Transmit a message from ireallycode.com to Analytics Hub"""

    # Get the conversation
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check authorization
    if (
        conversation.starter_user_id != current_user.id
        and conversation.recipient_user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this conversation"
        )

    # Get the message
    message = (
        db.query(models.ConversationMessage)
        .filter(
            models.ConversationMessage.id == message_id,
            models.ConversationMessage.conversation_id == conversation_id,
        )
        .first()
    )

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Transmit to Analytics Hub
    result = await external_service.send_message_to_analytics_hub(
        db, conversation.request_id, message.id, message.content
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to transmit message")

    # Update message to mark as transmitted
    # If you have a field for this:
    # message.transmitted_to_external = True
    # db.commit()

    return {
        "status": "success",
        "message": "Message transmitted successfully",
        "destination": "analytics-hub",
    }


@router.post("/{conversation_id}/messages/{message_id}/transmit")
async def transmit_message(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    """Transmit a message from ireallycode.com to Analytics Hub"""
    try:
        # Get the message
        message = (
            db.query(models.ConversationMessage)
            .filter(
                models.ConversationMessage.id == message_id,
                models.ConversationMessage.conversation_id == conversation_id,
            )
            .first()
        )

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Get the conversation
        conversation = (
            db.query(models.Conversation)
            .filter(models.Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get the request
        request = (
            db.query(models.Request)
            .filter(models.Request.id == conversation.request_id)
            .first()
        )

        if (
            not request
            or not request.external_metadata
            or "analytics_hub_id" not in request.external_metadata
        ):
            raise HTTPException(
                status_code=400, detail="No external ticket reference found"
            )

        # Get analytics_hub_id
        analytics_hub_id = request.external_metadata["analytics_hub_id"]

        # Call the webhook
        result = send_message_webhook(
            ticket_id=analytics_hub_id,
            message_content=message.content,
            message_id=f"ryze-msg-{message.id}",
            sender_type="support",
            sender_name=current_user.username,
            sender_id=str(current_user.id),
        )

        return {"status": "success", "message": "Message transmitted successfully"}

    except Exception as e:
        import traceback

        logger.error(f"Error transmitting message: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
