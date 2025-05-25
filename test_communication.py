# test_communication.py
import asyncio
import httpx
import sys
from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models import Request, Conversation, ConversationMessage, User
from app.utils.external_service import send_message_to_analytics_hub
import json


async def test_message_sending():
    # Get database session
    db = next(get_db())

    # Find the most recent external support ticket request
    external_requests = (
        db.query(Request)
        .filter(Request.external_metadata.is_not(None))
        .order_by(Request.created_at.desc())
        .all()
    )

    if not external_requests:
        print("No requests with external metadata found")
        return

    # Print the requests for selection
    print("Recent requests with external metadata:")
    for i, req in enumerate(external_requests):
        title = req.title[:50] + "..." if len(req.title) > 50 else req.title
        print(f"{i+1}. ID: {req.id} - {title}")

    # Allow selecting a request
    selected = 0
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        selected = int(sys.argv[1]) - 1
        if selected < 0 or selected >= len(external_requests):
            print(f"Invalid selection. Using the first request.")
            selected = 0

    request = external_requests[selected]

    # Print the full external metadata for debugging
    print(f"\nFull external metadata for request {request.id}:")
    print(json.dumps(request.external_metadata, indent=2))

    # Find the conversation
    conversation = (
        db.query(Conversation).filter(Conversation.request_id == request.id).first()
    )

    if not conversation:
        print(f"No conversation found for request {request.id}")
        return

    # Get developer user
    developer = db.query(User).filter(User.user_type == "developer").first()
    if not developer:
        print("No developer user found. Using system user.")
        developer = db.query(User).filter(User.email == "system@ryze.ai").first()
        if not developer:
            print("No system user found. Cannot proceed.")
            return

    # Create a test message
    new_message_content = (
        "This is a test message sent programmatically to Analytics Hub"
        if len(sys.argv) <= 2
        else sys.argv[2]
    )

    message = ConversationMessage(
        conversation_id=conversation.id,
        user_id=developer.id,
        content=new_message_content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    print(f"Created message with ID {message.id} in conversation {conversation.id}")

    # Now we need to decide what ID to use for the Analytics Hub ticket

    # Try to extract the actual ticket ID from response data
    # Check if we have a 'response' field in the external_metadata that contains the Analytics Hub ticket ID
    analytics_hub_ticket_id = None

    # First check if we have a field named 'analytics_hub_id' or similar
    possible_keys = [
        "analytics_hub_ticket_id",
        "analytics_hub_conversation_id",
        "ticket_id",
        "analytics_hub_id",
        "external_ticket_id",
    ]

    for key in possible_keys:
        if key in request.external_metadata:
            analytics_hub_ticket_id = request.external_metadata[key]
            print(
                f"Found Analytics Hub ticket ID in '{key}': {analytics_hub_ticket_id}"
            )
            break

    # If not found, ask the user to provide it
    if not analytics_hub_ticket_id:
        print("\nNo Analytics Hub ticket ID found in metadata.")
        input_id = input(
            "Please enter the Analytics Hub ticket ID (usually a number from the UI): "
        )
        if input_id:
            analytics_hub_ticket_id = input_id.strip()

            # Add it to the metadata for future use
            request.external_metadata["analytics_hub_ticket_id"] = (
                analytics_hub_ticket_id
            )
            db.commit()
            print(
                f"Added Analytics Hub ticket ID {analytics_hub_ticket_id} to request metadata"
            )

    # Try sending the message to the specific Analytics Hub ticket
    # Add this to your test_communication.py script for direct testing

    # ...

    # Try sending the message directly with the right schema
    if analytics_hub_ticket_id:
        print(
            f"\nSending message directly to Analytics Hub ticket ID: {analytics_hub_ticket_id}"
        )

        api_url = getattr(
            settings, "ANALYTICS_HUB_API_URL", "https://analytics-hub.xyz/api"
        )
        api_key = getattr(settings, "ANALYTICS_HUB_API_KEY", settings.EXTERNAL_API_KEY)

        # Use the EXACT payload format required by Analytics Hub's API
        payload = {
            "message_id": str(message.id),
            "content": message.content,
            "sender_type": "support",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/support/tickets/{analytics_hub_ticket_id}/messages",
                    headers={"Content-Type": "application/json", "X-API-Key": api_key},
                    json=payload,
                    timeout=10.0,
                )

                response.raise_for_status()
                print(f"Direct API call successful: {response.status_code}")
                print(f"Response: {response.json()}")
                return
        except Exception as e:
            print(f"Direct API call failed: {str(e)}")

    # If we get here, try the normal way
    print(f"\nTrying normal send function with request ID {request.id}...")

    result = await send_message_to_analytics_hub(
        db, request_id=request.id, message_id=message.id, content=message.content
    )

    print(f"Result: {result}")


# Run the test
if __name__ == "__main__":
    from datetime import datetime
    from app.config import settings

    asyncio.run(test_message_sending())
