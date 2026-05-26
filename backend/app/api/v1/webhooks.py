"""
Twilio Webhook Handlers
Handles incoming Twilio webhooks for call events
"""
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import Response
from typing import Optional

from app.services.call_service import CallService
from app.services.company_service import CompanyService
from app.schemas.call import CallCreate
from app.core.logging_config import get_logger
from app.core.exceptions import CompanyNotFoundError
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def generate_twiml_response(
    websocket_url: str,
    greeting_message: Optional[str] = None
) -> str:
    """
    Generate TwiML response to connect call to WebSocket

    Args:
        websocket_url: WebSocket URL for the call
        greeting_message: Optional greeting message to speak before connecting

    Returns:
        TwiML XML string
    """
    twiml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<Response>']

    # Add greeting if provided
    if greeting_message:
        # Escape XML special characters
        greeting_escaped = (
            greeting_message
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
        twiml_parts.append(f'  <Say>{greeting_escaped}</Say>')

    # Connect to WebSocket
    twiml_parts.append('  <Connect>')
    twiml_parts.append(f'    <Stream url="{websocket_url}" />')
    twiml_parts.append('  </Connect>')
    twiml_parts.append('</Response>')

    return '\n'.join(twiml_parts)


@router.post(
    "/voice",
    summary="Handle incoming call",
    description="Twilio webhook for incoming calls"
)
@router.post(
    "/incoming-call",
    summary="Handle incoming call (alias)",
    description="Twilio webhook for incoming calls"
)
async def handle_incoming_call(request: Request):
    """
    Handle incoming call from Twilio

    This webhook receives Twilio's incoming call event, looks up the company
    by phone number, creates a call record, and returns TwiML to connect the
    call to our WebSocket handler.

    Expected Twilio POST parameters:
        - CallSid: Unique call identifier
        - From: Caller's phone number
        - To: Called phone number (our Twilio number)
        - Direction: "inbound"
        - CallStatus: "ringing", "in-progress", etc.

    Returns:
        TwiML XML response with WebSocket connection instructions

    Raises:
        HTTPException 404: If company not found for the called number
        HTTPException 500: If webhook processing fails
    """
    try:
        # Parse form data from Twilio
        form_data = await request.form()

        # Extract Twilio parameters
        call_sid = form_data.get("CallSid")
        from_number = form_data.get("From")
        to_number = form_data.get("To")
        direction = form_data.get("Direction", "inbound")
        call_status = form_data.get("CallStatus")

        logger.info(
            f"Incoming call: {call_sid} | From: {from_number} | To: {to_number} | Status: {call_status}"
        )

        # Validate required parameters
        if not all([call_sid, from_number, to_number]):
            logger.error("Missing required Twilio parameters")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )

        # Look up company by phone number
        company_service = CompanyService()
        try:
            company = await company_service.get_company_by_phone(to_number)
        except CompanyNotFoundError:
            logger.warning(f"No company found for phone number: {to_number}")

            # Return TwiML with error message
            error_twiml = generate_twiml_response(
                websocket_url="",
                greeting_message="Sorry, this service is not available at this number."
            )
            # Remove the Stream element since we don't have a valid company
            error_twiml = error_twiml.replace('  <Connect>\n    <Stream url="" />\n  </Connect>\n', '')

            return Response(content=error_twiml, media_type="application/xml")

        # Check if company is active
        if company.status != "active":
            logger.warning(f"Company {company.id} is not active (status: {company.status})")

            status_messages = {
                "inactive": "This service is currently inactive.",
                "suspended": "This service has been suspended. Please contact support."
            }
            message = status_messages.get(company.status, "This service is not available.")

            error_twiml = generate_twiml_response(
                websocket_url="",
                greeting_message=message
            )
            error_twiml = error_twiml.replace('  <Connect>\n    <Stream url="" />\n  </Connect>\n', '')

            return Response(content=error_twiml, media_type="application/xml")

        # Create call record
        call_service = CallService()
        call_data = CallCreate(
            call_sid=call_sid,
            company_id=company.id,
            from_number=from_number,
            to_number=to_number,
            direction=direction
        )

        try:
            await call_service.create_call(call_data)
            logger.info(f"Call record created: {call_sid} for company {company.id}")
        except Exception as e:
            # Log error but don't fail the webhook - we still want to connect the call
            logger.error(f"Failed to create call record: {str(e)}", exc_info=True)

        # Build WebSocket URL
        # Format: wss://your-domain/ws/call/{call_sid}
        base_url = settings.websocket_base_url or "wss://your-domain.com"
        websocket_url = f"{base_url}/ws/call/{call_sid}"

        # Generate TwiML response (no greeting - will be sent via WebSocket)
        twiml = generate_twiml_response(websocket_url=websocket_url)

        logger.info(f"Returning TwiML for call {call_sid} → WebSocket: {websocket_url}")

        return Response(content=twiml, media_type="application/xml")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)

        # Return generic error TwiML
        error_twiml = generate_twiml_response(
            websocket_url="",
            greeting_message="Sorry, we're experiencing technical difficulties. Please try again later."
        )
        error_twiml = error_twiml.replace('  <Connect>\n    <Stream url="" />\n  </Connect>\n', '')

        return Response(content=error_twiml, media_type="application/xml")


@router.post(
    "/call-status",
    summary="Handle call status updates",
    description="Twilio webhook for call status changes"
)
async def handle_call_status(request: Request):
    """
    Handle call status updates from Twilio

    This webhook receives status updates throughout the call lifecycle:
    - queued, ringing, in-progress, completed, busy, failed, no-answer, canceled

    Expected Twilio POST parameters:
        - CallSid: Unique call identifier
        - CallStatus: Current call status
        - CallDuration: Duration in seconds (for completed calls)

    Returns:
        Empty 200 OK response

    Note:
        This is optional - we primarily handle status updates via WebSocket.
        This webhook provides a backup mechanism for tracking call completion.
    """
    try:
        # Parse form data from Twilio
        form_data = await request.form()

        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        call_duration = form_data.get("CallDuration")

        logger.info(f"Call status update: {call_sid} | Status: {call_status} | Duration: {call_duration}")

        # TODO: Update call record in database if needed
        # This is optional since we handle most status updates via WebSocket
        # Uncomment if you want to use this as a backup mechanism:
        #
        # call_service = CallService()
        # await call_service.update_call_by_sid(
        #     call_sid=call_sid,
        #     data=CallUpdate(
        #         status=call_status,
        #         duration=int(call_duration) if call_duration else None
        #     )
        # )

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Call status webhook failed: {str(e)}", exc_info=True)
        # Return 200 anyway - don't want Twilio to retry
        return Response(status_code=200)


@router.get(
    "/health",
    summary="Health check",
    description="Health check endpoint for webhook monitoring"
)
async def webhook_health():
    """
    Health check endpoint

    Returns:
        Simple OK response
    """
    return {"status": "ok", "service": "webhooks"}


# Export router
__all__ = ["router"]
