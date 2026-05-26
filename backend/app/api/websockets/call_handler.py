"""
WebSocket Call Handler
Handles real-time bidirectional audio streaming with Twilio Media Streams
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
import json
import asyncio
import base64
from datetime import datetime

from app.services.voice_pipeline_service import VoicePipelineService
from app.services.call_service import CallService
from app.services.agent_service import AgentService
from app.schemas.call import CallUpdate, CallTranscriptMessage
from app.core.logging_config import get_logger
from app.core.exceptions import CallNotFoundError

logger = get_logger(__name__)


class CallHandler:
    """
    Handles WebSocket connection for a single call
    """

    def __init__(self, call_sid: str):
        """
        Initialize call handler

        Args:
            call_sid: Twilio Call SID
        """
        self.call_sid = call_sid
        self.voice_pipeline = VoicePipelineService()
        self.call_service = CallService()
        self.agent_service = AgentService()

        # Audio buffer - use double buffering to avoid dropping audio
        self.audio_buffer: bytes = b""
        self.buffer_duration_ms: int = 0
        self.min_buffer_ms: int = 600  # Minimum 600ms before considering processing
        self.max_buffer_ms: int = 10000  # Maximum 10 seconds (safety valve for very long speech)
        self.silence_threshold_ms: int = 500  # 500ms of silence = end of speech
        self.last_audio_time: Optional[float] = None  # Timestamp of last audio chunk
        self.is_processing: bool = False  # Track processing state
        self.processing_lock: asyncio.Lock = asyncio.Lock()  # Prevent concurrent processing
        self.silence_detector_task: Optional[asyncio.Task] = None  # Single silence detector

        # Session state
        self.company_id: Optional[str] = None
        self.stream_sid: Optional[str] = None
        self.is_active: bool = False
        self.greeting_sent: bool = False

        # Statistics
        self.start_time: Optional[datetime] = None
        self.total_messages: int = 0
        self.total_audio_processed: int = 0

    async def handle_connection(self, websocket: WebSocket):
        """
        Handle WebSocket connection lifecycle

        Args:
            websocket: FastAPI WebSocket connection
        """
        try:
            # Accept WebSocket connection
            await websocket.accept()
            logger.info(f"WebSocket connected: {self.call_sid}")

            self.is_active = True
            self.start_time = datetime.utcnow()

            # Main message loop
            while self.is_active:
                try:
                    # Receive message from Twilio
                    raw_message = await websocket.receive_text()
                    message = json.loads(raw_message)

                    self.total_messages += 1

                    # Handle message based on event type
                    event = message.get("event")

                    if event == "connected":
                        await self._handle_connected(message)

                    elif event == "start":
                        await self._handle_start(websocket, message)

                    elif event == "media":
                        await self._handle_media(websocket, message)

                    elif event == "stop":
                        await self._handle_stop(websocket, message)
                        break

                    elif event == "mark":
                        # Mark event indicates media was played
                        logger.debug(f"Media mark received: {message.get('mark')}")

                    else:
                        logger.warning(f"Unknown event type: {event}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from Twilio: {str(e)}")

                except asyncio.TimeoutError:
                    logger.warning(f"WebSocket timeout: {self.call_sid}")
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {self.call_sid}")

        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}", exc_info=True)

        finally:
            # Cleanup
            await self._cleanup(websocket)

    async def _handle_connected(self, message: Dict[str, Any]):
        """
        Handle 'connected' event from Twilio

        Args:
            message: Connected event message
        """
        logger.info(f"Call connected: {self.call_sid}")
        logger.debug(f"Connected message: {message}")

    async def _handle_start(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Handle 'start' event from Twilio

        This event signals the beginning of media streaming.

        Args:
            websocket: WebSocket connection
            message: Start event message
        """
        try:
            # Extract start event details
            start_data = message.get("start", {})
            self.stream_sid = start_data.get("streamSid")

            logger.info(f"Media stream started: {self.call_sid} (stream_sid={self.stream_sid})")

            # Look up call in database to get company_id
            try:
                call = await self.call_service.get_call_by_sid(self.call_sid)
                self.company_id = call.company_id
                logger.info(f"Call {self.call_sid} belongs to company {self.company_id}")
            except CallNotFoundError:
                logger.error(f"Call not found in database: {self.call_sid}")
                # Send error message and close
                await self._send_error_message(
                    websocket,
                    "Sorry, we couldn't process your call. Please try again."
                )
                self.is_active = False
                return

            # Update call status to in_progress
            await self.call_service.update_call_by_sid(
                call_sid=self.call_sid,
                data=CallUpdate(status="in_progress")
            )

            # Initialize voice pipeline session
            await self.voice_pipeline.initialize_session(
                call_sid=self.call_sid,
                company_id=self.company_id
            )

            # Get agent config for greeting
            agent_config = await self.agent_service.get_agent_config(self.company_id)

            # Send greeting message if configured
            if agent_config.greeting_message and not self.greeting_sent:
                await self._send_agent_message(websocket, agent_config.greeting_message)
                self.greeting_sent = True

            # Start the silence detector task
            if not self.silence_detector_task:
                self.silence_detector_task = asyncio.create_task(
                    self._continuous_silence_detector(websocket)
                )
                logger.debug("Started continuous silence detector")

        except Exception as e:
            logger.error(f"Error handling start event: {str(e)}", exc_info=True)
            await self._send_error_message(
                websocket,
                "Sorry, we're experiencing technical difficulties."
            )
            self.is_active = False

    async def _handle_media(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Handle 'media' event from Twilio

        This event contains audio chunks from the caller.

        Args:
            websocket: WebSocket connection
            message: Media event message
        """
        try:
            # Extract media payload
            media_data = message.get("media", {})
            audio_base64 = media_data.get("payload")

            if not audio_base64:
                logger.warning("Received media event without payload")
                return

            # IMPORTANT: Continue buffering audio even if processing
            # (we use double-buffering to avoid dropping audio)

            # Decode base64 chunk to raw mulaw bytes and add to buffer
            # Each media chunk is ~20ms of audio
            # CRITICAL: We must decode each chunk and concatenate raw bytes,
            # not concatenate base64 strings (that creates corrupted data)
            mulaw_chunk = base64.b64decode(audio_base64)
            self.audio_buffer += mulaw_chunk
            self.buffer_duration_ms += 20  # Twilio sends 20ms chunks
            self.last_audio_time = asyncio.get_event_loop().time()

            # The continuous silence detector task handles processing
            # No need to create tasks here - it checks every 100ms

        except Exception as e:
            logger.error(f"Error handling media event: {str(e)}", exc_info=True)

    async def _handle_stop(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Handle 'stop' event from Twilio

        This event signals the end of media streaming.

        Args:
            websocket: WebSocket connection
            message: Stop event message
        """
        logger.info(f"Media stream stopped: {self.call_sid}")

        # Process any remaining buffered audio
        if self.audio_buffer:
            try:
                await self._process_buffer(websocket)
            except Exception as e:
                logger.error(f"Error processing final buffer: {str(e)}")

        # Mark call as completed
        try:
            # Get final session state
            session = self.voice_pipeline.get_session(self.call_sid)

            # Calculate duration
            duration = None
            if self.start_time:
                duration = int((datetime.utcnow() - self.start_time).total_seconds())

            # Build transcript
            transcript_messages = []
            if session:
                for msg in session.messages:
                    transcript_messages.append(
                        CallTranscriptMessage(
                            role=msg["role"],
                            content=msg["content"],
                            timestamp=msg["timestamp"]
                        )
                    )

            # Update call record
            await self.call_service.update_call_by_sid(
                call_sid=self.call_sid,
                data=CallUpdate(
                    status="completed",
                    duration=duration,
                    transcript=transcript_messages
                )
            )

            logger.info(
                f"Call completed: {self.call_sid} | "
                f"Duration: {duration}s | "
                f"Messages: {len(transcript_messages)}"
            )

        except Exception as e:
            logger.error(f"Error finalizing call: {str(e)}", exc_info=True)

        self.is_active = False

    async def _continuous_silence_detector(self, websocket: WebSocket):
        """
        Continuously monitors for silence and triggers processing

        This task runs in the background throughout the call lifecycle.
        It checks every 100ms if:
        1. We have minimum audio buffered (600ms)
        2. No new audio has arrived for silence_threshold_ms (500ms)
        3. We're not currently processing

        When all conditions are met, it triggers buffer processing.

        Args:
            websocket: WebSocket connection
        """
        try:
            logger.debug("Continuous silence detector started")

            while self.is_active:
                # Check every 100ms
                await asyncio.sleep(0.1)

                # Skip if no audio buffered yet or already processing
                if not self.audio_buffer or not self.last_audio_time or self.is_processing:
                    continue

                # Skip if buffer too small
                if self.buffer_duration_ms < self.min_buffer_ms:
                    continue

                # Calculate silence duration
                current_time = asyncio.get_event_loop().time()
                silence_duration_ms = (current_time - self.last_audio_time) * 1000

                # Check if we should process:
                # 1. Silence threshold exceeded (normal case)
                # 2. Buffer is too large (safety valve)
                should_process = (
                    silence_duration_ms >= self.silence_threshold_ms or
                    self.buffer_duration_ms >= self.max_buffer_ms
                )

                if should_process:
                    logger.info(
                        f"Triggering processing: buffer={self.buffer_duration_ms}ms, "
                        f"silence={silence_duration_ms:.0f}ms, "
                        f"max_exceeded={self.buffer_duration_ms >= self.max_buffer_ms}"
                    )
                    await self._process_buffer(websocket)

        except asyncio.CancelledError:
            logger.debug("Continuous silence detector cancelled")
        except Exception as e:
            logger.error(f"Error in continuous silence detector: {str(e)}", exc_info=True)

    async def _process_buffer(self, websocket: WebSocket):
        """
        Process accumulated audio buffer through voice pipeline

        Args:
            websocket: WebSocket connection
        """
        # Use lock to prevent concurrent processing
        async with self.processing_lock:
            try:
                if not self.audio_buffer or not self.company_id:
                    return

                # Set processing flag
                self.is_processing = True

                # Encode the raw mulaw buffer to base64 for the pipeline
                audio_base64 = base64.b64encode(self.audio_buffer).decode('utf-8')

                logger.debug(
                    f"Processing audio buffer: {len(audio_base64)} chars base64, "
                    f"{len(self.audio_buffer)} bytes mulaw, {self.buffer_duration_ms}ms"
                )

                # Clear buffer immediately to start collecting next utterance
                self.audio_buffer = b""
                self.buffer_duration_ms = 0

                # Process through voice pipeline
                result = await self.voice_pipeline.process_audio(
                    audio_base64=audio_base64,
                    call_sid=self.call_sid,
                    company_id=self.company_id
                )

                self.total_audio_processed += 1

                # Log latency
                logger.info(
                    f"Voice pipeline completed: {self.call_sid} | "
                    f"Latency: {result['latency_ms']}ms | "
                    f"Transcript: '{result['transcript'][:50]}...'"
                )

                # Log detailed latency breakdown for optimization
                logger.debug(f"Latency breakdown: {result['latency_breakdown']}")

                # Send response audio to Twilio (only if connection is still open)
                if result['response_audio'] and self.is_active:
                    await self._send_audio(websocket, result['response_audio'])

            except Exception as e:
                logger.error(f"Error processing audio buffer: {str(e)}", exc_info=True)

                # Send error message to caller (only if connection is still open)
                if self.is_active:
                    try:
                        await self._send_error_message(
                            websocket,
                            "I'm sorry, I didn't catch that. Could you please repeat?"
                        )
                    except Exception:
                        pass  # Ignore errors in error handling

            finally:
                # Always clear processing flag
                self.is_processing = False

    async def _send_audio(self, websocket: WebSocket, audio_base64: str):
        """
        Send audio to Twilio for playback

        Args:
            websocket: WebSocket connection
            audio_base64: Base64-encoded mulaw audio
        """
        try:
            if not self.is_active or not self.stream_sid:
                logger.warning("Cannot send audio - connection not active")
                return

            # Split audio into chunks (Twilio expects ~20ms chunks)
            # For simplicity, we'll send the entire audio in one media event
            # In production, you might want to chunk this for smoother playback

            media_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_base64
                }
            }

            await websocket.send_text(json.dumps(media_message))

            logger.debug(f"Sent audio to Twilio: {len(audio_base64)} chars")

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected while sending audio")
            self.is_active = False
        except Exception as e:
            # Don't log full traceback for connection errors
            if "ConnectionClosed" in str(type(e).__name__) or "ClientDisconnected" in str(type(e).__name__):
                logger.info(f"Connection closed while sending audio: {type(e).__name__}")
                self.is_active = False
            else:
                logger.error(f"Error sending audio: {str(e)}", exc_info=True)

    async def _send_agent_message(self, websocket: WebSocket, text: str):
        """
        Convert text to speech and send to Twilio

        Args:
            websocket: WebSocket connection
            text: Text message to speak
        """
        try:
            # Use voice pipeline to synthesize speech
            result = await self.voice_pipeline.synthesize_greeting(
                text=text,
                company_id=self.company_id
            )

            # Send audio
            await self._send_audio(websocket, result['audio_base64'])

            logger.info(f"Sent greeting: '{text[:50]}...'")

        except Exception as e:
            logger.error(f"Error sending agent message: {str(e)}", exc_info=True)

    async def _send_error_message(self, websocket: WebSocket, error_text: str):
        """
        Send error message to caller

        Args:
            websocket: WebSocket connection
            error_text: Error message to speak
        """
        try:
            await self._send_agent_message(websocket, error_text)
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}", exc_info=True)

    async def _cleanup(self, websocket: WebSocket):
        """
        Cleanup resources after call ends

        Args:
            websocket: WebSocket connection
        """
        try:
            # Cancel silence detector task
            if self.silence_detector_task and not self.silence_detector_task.done():
                self.silence_detector_task.cancel()
                try:
                    await self.silence_detector_task
                except asyncio.CancelledError:
                    pass
                logger.debug("Cancelled silence detector task")

            # Close voice pipeline session
            if self.call_sid:
                self.voice_pipeline.cleanup_session(self.call_sid)

            # Close WebSocket if still open
            try:
                await websocket.close()
            except:
                pass

            # Log statistics
            if self.start_time:
                duration = (datetime.utcnow() - self.start_time).total_seconds()
                logger.info(
                    f"Call cleanup: {self.call_sid} | "
                    f"Duration: {duration:.1f}s | "
                    f"Messages: {self.total_messages} | "
                    f"Audio processed: {self.total_audio_processed}"
                )

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)


# FastAPI WebSocket endpoint
async def handle_call_websocket(websocket: WebSocket, call_sid: str):
    """
    FastAPI WebSocket endpoint handler

    Args:
        websocket: FastAPI WebSocket connection
        call_sid: Twilio Call SID from URL path
    """
    handler = CallHandler(call_sid)
    await handler.handle_connection(websocket)


# Export
__all__ = ["handle_call_websocket", "CallHandler"]
