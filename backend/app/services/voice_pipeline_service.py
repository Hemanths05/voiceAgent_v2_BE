"""
Voice Pipeline Service (MOST CRITICAL)
Orchestrates real-time voice processing: STT → RAG → LLM → TTS

Target Latency: <2 seconds end-to-end
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.core.logging_config import get_logger
from app.core.exceptions import (
    STTProviderError,
    LLMProviderError,
    TTSProviderError,
    PipelineError
)
from app.providers.factories.stt_factory import STTFactory
from app.providers.factories.llm_factory import LLMFactory
from app.providers.factories.tts_factory import TTSFactory
from app.providers.base.llm_base import LLMMessage
from app.services.knowledge_service import KnowledgeService
from app.services.agent_service import AgentService
from app.utils.audio import AudioConverter

logger = get_logger(__name__)


class ConversationSession:
    """
    Manages conversation state for a single call

    Stores:
    - Conversation history (last N messages)
    - Call metadata
    - Timing metrics
    """

    def __init__(
        self,
        call_sid: str,
        company_id: str,
        history_limit: int = 10
    ):
        self.call_sid = call_sid
        self.company_id = company_id
        self.history_limit = history_limit
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    def add_message(self, role: str, content: str) -> None:
        """
        Add message to conversation history

        Args:
            role: Message role (user, assistant)
            content: Message content
        """
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        })

        # Keep only last N messages
        if len(self.messages) > self.history_limit:
            self.messages = self.messages[-self.history_limit:]

        self.last_activity = datetime.utcnow()

    def get_llm_messages(self, system_prompt: str) -> List[LLMMessage]:
        """
        Get conversation history formatted for LLM

        Args:
            system_prompt: System prompt to prepend

        Returns:
            List of LLM messages
        """
        messages = [LLMMessage(role="system", content=system_prompt)]

        for msg in self.messages:
            messages.append(
                LLMMessage(role=msg["role"], content=msg["content"])
            )

        return messages

    def get_transcript(self) -> List[Dict[str, Any]]:
        """
        Get full conversation transcript

        Returns:
            List of message dictionaries
        """
        return self.messages.copy()


class VoicePipelineService:
    """
    Real-time voice processing pipeline orchestrator

    Pipeline Flow:
    1. Audio Conversion: mulaw base64 → PCM 16kHz WAV
    2. STT: Transcribe audio → text
    3. RAG: Search knowledge base (if enabled)
    4. LLM: Generate response with context
    5. TTS: Synthesize speech from response
    6. Audio Conversion: TTS output → mulaw base64

    Optimizations:
    - Parallel operations where possible
    - Provider fallback on failure
    - Graceful degradation (e.g., skip RAG on error)
    - Comprehensive error handling
    """

    def __init__(self):
        """Initialize voice pipeline service"""
        self.knowledge_service = KnowledgeService()
        self.agent_service = AgentService()
        self.audio_converter = AudioConverter()

        # In-memory session storage
        # TODO: Move to Redis for distributed systems
        self.sessions: Dict[str, ConversationSession] = {}

        logger.info("Voice Pipeline Service initialized")

    async def process_audio(
        self,
        audio_base64: str,
        call_sid: str,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Process audio through full pipeline

        Args:
            audio_base64: Base64 encoded mulaw audio from Twilio
            call_sid: Twilio Call SID
            company_id: Company ID

        Returns:
            Dict with:
                - response_audio: Base64 encoded mulaw audio for Twilio
                - transcript: User's transcribed message
                - response_text: Agent's response text
                - latency_ms: Total processing time
                - latency_breakdown: Breakdown by stage

        Raises:
            PipelineError: If pipeline fails
        """
        pipeline_start = time.time()
        latency_breakdown = {}

        try:
            logger.info(f"Processing audio for call {call_sid}")

            # Get or create session
            session = self._get_or_create_session(call_sid, company_id)

            # Step 1: Load agent config
            config_start = time.time()
            agent_config = await self.agent_service.get_agent_config(company_id)
            latency_breakdown["config_load"] = (time.time() - config_start) * 1000

            # Step 2: Audio conversion (mulaw → WAV)
            audio_start = time.time()
            wav_audio = self.audio_converter.twilio_to_stt_format(
                audio_base64,
                target_sample_rate=16000
            )
            latency_breakdown["audio_conversion_in"] = (time.time() - audio_start) * 1000

            # Step 3: STT (Speech-to-Text)
            stt_start = time.time()
            transcript = await self._transcribe_audio(
                wav_audio,
                agent_config.stt_provider,
                agent_config.stt_model,
                agent_config.fallback_stt_provider
            )
            latency_breakdown["stt"] = (time.time() - stt_start) * 1000

            if not transcript.strip():
                logger.warning(f"Empty transcript for call {call_sid}")
                raise PipelineError("Failed to transcribe audio")

            logger.info(f"Transcript: {transcript}")

            # Add user message to history
            session.add_message("user", transcript)

            # Step 4: RAG (if enabled)
            rag_context = ""
            if agent_config.enable_rag:
                rag_start = time.time()
                try:
                    rag_context = await self.knowledge_service.build_rag_context(
                        query=transcript,
                        company_id=company_id,
                        top_k=agent_config.rag_top_k
                    )
                    latency_breakdown["rag"] = (time.time() - rag_start) * 1000
                except Exception as e:
                    logger.error(f"RAG failed, continuing without context: {str(e)}")
                    latency_breakdown["rag"] = (time.time() - rag_start) * 1000

            # Step 5: Build LLM prompt
            prompt_start = time.time()
            llm_messages = self._build_llm_messages(
                session=session,
                system_prompt=agent_config.system_prompt,
                rag_context=rag_context
            )
            latency_breakdown["prompt_build"] = (time.time() - prompt_start) * 1000

            # Step 6: LLM generation
            llm_start = time.time()
            response_text = await self._generate_response(
                messages=llm_messages,
                llm_provider=agent_config.llm_provider,
                llm_model=agent_config.llm_model,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens,
                top_p=agent_config.top_p,
                fallback_provider=agent_config.fallback_llm_provider
            )
            latency_breakdown["llm"] = (time.time() - llm_start) * 1000

            if not response_text.strip():
                logger.error(f"Empty LLM response for call {call_sid}")
                response_text = "I'm sorry, I didn't understand that. Could you please repeat?"

            logger.info(f"Response: {response_text}")

            # Add assistant message to history
            session.add_message("assistant", response_text)

            # Step 7: TTS (Text-to-Speech)
            tts_start = time.time()
            tts_audio, tts_format, tts_sample_rate = await self._synthesize_speech(
                text=response_text,
                tts_provider=agent_config.tts_provider,
                tts_model=agent_config.tts_model,
                voice_id=agent_config.voice_id,
                voice_settings=agent_config.voice_settings,
                fallback_provider=agent_config.fallback_tts_provider
            )
            latency_breakdown["tts"] = (time.time() - tts_start) * 1000

            # Step 8: Audio conversion (TTS output → mulaw)
            audio_out_start = time.time()
            response_audio_base64 = self.audio_converter.tts_to_twilio_format(
                tts_audio,
                input_format=tts_format,
                input_sample_rate=tts_sample_rate if tts_format == "pcm" else None
            )
            latency_breakdown["audio_conversion_out"] = (time.time() - audio_out_start) * 1000

            # Calculate total latency
            total_latency_ms = (time.time() - pipeline_start) * 1000

            logger.info(
                f"Pipeline complete for {call_sid}: {total_latency_ms:.2f}ms "
                f"(STT: {latency_breakdown['stt']:.0f}ms, "
                f"LLM: {latency_breakdown['llm']:.0f}ms, "
                f"TTS: {latency_breakdown['tts']:.0f}ms)"
            )

            return {
                "response_audio": response_audio_base64,
                "transcript": transcript,
                "response_text": response_text,
                "latency_ms": total_latency_ms,
                "latency_breakdown": latency_breakdown
            }

        except PipelineError:
            raise
        except Exception as e:
            logger.error(f"Pipeline error for {call_sid}: {str(e)}", exc_info=True)
            raise PipelineError(f"Voice pipeline failed: {str(e)}")

    async def _transcribe_audio(
        self,
        audio_data: bytes,
        provider: str,
        model: Optional[str],
        fallback_provider: Optional[str]
    ) -> str:
        """
        Transcribe audio with fallback

        Args:
            audio_data: Audio bytes (WAV format)
            provider: Primary STT provider
            model: Model name
            fallback_provider: Fallback provider on failure

        Returns:
            Transcribed text

        Raises:
            STTProviderError: If transcription fails
        """
        try:
            stt = STTFactory.create(provider, model=model)
            response = await stt.transcribe(audio_data)
            return response.text

        except Exception as e:
            logger.error(f"STT failed with {provider}: {str(e)}")

            # Try fallback provider
            if fallback_provider:
                try:
                    logger.info(f"Trying fallback STT provider: {fallback_provider}")
                    stt_fallback = STTFactory.create(fallback_provider)
                    response = await stt_fallback.transcribe(audio_data)
                    return response.text
                except Exception as fallback_e:
                    logger.error(f"Fallback STT also failed: {str(fallback_e)}")

            raise STTProviderError(provider, f"STT transcription failed: {str(e)}")

    def _build_llm_messages(
        self,
        session: ConversationSession,
        system_prompt: str,
        rag_context: str
    ) -> List[LLMMessage]:
        """
        Build LLM messages with system prompt, RAG context, and history

        Args:
            session: Conversation session
            system_prompt: System prompt
            rag_context: RAG context from knowledge base

        Returns:
            List of LLM messages
        """
        # Enhance system prompt with RAG context
        enhanced_system_prompt = system_prompt
        if rag_context:
            enhanced_system_prompt = f"{system_prompt}\n\n{rag_context}"

        return session.get_llm_messages(enhanced_system_prompt)

    async def _generate_response(
        self,
        messages: List[LLMMessage],
        llm_provider: str,
        llm_model: Optional[str],
        temperature: float,
        max_tokens: int,
        top_p: float,
        fallback_provider: Optional[str]
    ) -> str:
        """
        Generate LLM response with fallback

        Args:
            messages: Conversation messages
            llm_provider: Primary LLM provider
            llm_model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            top_p: Top-p sampling
            fallback_provider: Fallback provider on failure

        Returns:
            Generated response text

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            llm = LLMFactory.create(
                llm_provider,
                model=llm_model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
            response = await llm.generate(messages)
            return response.content

        except Exception as e:
            logger.error(f"LLM failed with {llm_provider}: {str(e)}")

            # Try fallback provider
            if fallback_provider:
                try:
                    logger.info(f"Trying fallback LLM provider: {fallback_provider}")
                    llm_fallback = LLMFactory.create(
                        fallback_provider,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p
                    )
                    response = await llm_fallback.generate(messages)
                    return response.content
                except Exception as fallback_e:
                    logger.error(f"Fallback LLM also failed: {str(fallback_e)}")

            raise LLMProviderError(f"LLM generation failed: {str(e)}")

    async def _synthesize_speech(
        self,
        text: str,
        tts_provider: str,
        tts_model: Optional[str],
        voice_id: Optional[str],
        voice_settings: Optional[Dict[str, Any]],
        fallback_provider: Optional[str]
    ) -> Tuple[bytes, str, int]:
        """
        Synthesize speech with fallback

        Args:
            text: Text to synthesize
            tts_provider: Primary TTS provider
            tts_model: Model name
            voice_id: Voice ID
            voice_settings: Voice settings
            fallback_provider: Fallback provider on failure

        Returns:
            Tuple of (audio_bytes, audio_format, sample_rate)

        Raises:
            TTSProviderError: If synthesis fails
        """
        try:
            tts = TTSFactory.create(
                tts_provider,
                model=tts_model,
                voice_id=voice_id
            )

            kwargs = {}
            if voice_settings:
                kwargs.update(voice_settings)

            response = await tts.synthesize(text, **kwargs)
            return response.audio_data, response.audio_format, response.sample_rate

        except Exception as e:
            logger.error(f"TTS failed with {tts_provider}: {str(e)}")

            # Try fallback provider
            if fallback_provider:
                try:
                    logger.info(f"Trying fallback TTS provider: {fallback_provider}")
                    tts_fallback = TTSFactory.create(fallback_provider)
                    response = await tts_fallback.synthesize(text)
                    return response.audio_data, response.audio_format, response.sample_rate
                except Exception as fallback_e:
                    logger.error(f"Fallback TTS also failed: {str(fallback_e)}")

            raise TTSProviderError(tts_provider, f"TTS synthesis failed: {str(e)}")

    def _get_or_create_session(
        self,
        call_sid: str,
        company_id: str
    ) -> ConversationSession:
        """
        Get existing session or create new one

        Args:
            call_sid: Twilio Call SID
            company_id: Company ID

        Returns:
            Conversation session
        """
        if call_sid not in self.sessions:
            self.sessions[call_sid] = ConversationSession(
                call_sid=call_sid,
                company_id=company_id,
                history_limit=10  # Default, will be updated with agent config
            )
            logger.info(f"Created new session for call: {call_sid}")

        return self.sessions[call_sid]

    def get_session(self, call_sid: str) -> Optional[ConversationSession]:
        """
        Get existing session

        Args:
            call_sid: Twilio Call SID

        Returns:
            Conversation session or None
        """
        return self.sessions.get(call_sid)

    def cleanup_session(self, call_sid: str) -> None:
        """
        Clean up session after call ends

        Args:
            call_sid: Twilio Call SID
        """
        if call_sid in self.sessions:
            del self.sessions[call_sid]
            logger.info(f"Cleaned up session for call: {call_sid}")

    async def initialize_session(
        self,
        call_sid: str,
        company_id: str
    ) -> ConversationSession:
        """
        Initialize a new conversation session

        Args:
            call_sid: Twilio Call SID
            company_id: Company ID

        Returns:
            Created conversation session
        """
        session = self._get_or_create_session(call_sid, company_id)
        logger.info(f"Initialized session for call: {call_sid}")
        return session

    async def synthesize_greeting(
        self,
        text: str,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Synthesize a custom greeting message

        Args:
            text: Text to synthesize
            company_id: Company ID

        Returns:
            Dict with audio_base64 key containing mulaw audio
        """
        try:
            # Get agent config for TTS settings
            agent_config = await self.agent_service.get_agent_config(company_id)

            # Synthesize speech
            tts_audio, tts_format, tts_sample_rate = await self._synthesize_speech(
                text=text,
                tts_provider=agent_config.tts_provider,
                tts_model=agent_config.tts_model,
                voice_id=agent_config.voice_id,
                voice_settings=agent_config.voice_settings,
                fallback_provider=agent_config.fallback_tts_provider
            )

            # Convert to Twilio format
            audio_base64 = self.audio_converter.tts_to_twilio_format(
                tts_audio,
                input_format=tts_format,
                input_sample_rate=tts_sample_rate if tts_format == "pcm" else None
            )

            logger.info(f"Synthesized greeting: '{text[:50]}...'")

            return {"audio_base64": audio_base64}

        except Exception as e:
            logger.error(f"Error synthesizing greeting: {str(e)}", exc_info=True)
            # Return empty audio on error
            return {"audio_base64": ""}

    async def generate_greeting(
        self,
        company_id: str,
        call_sid: str
    ) -> str:
        """
        Generate greeting audio for call start

        Args:
            company_id: Company ID
            call_sid: Twilio Call SID

        Returns:
            Base64 encoded mulaw audio
        """
        try:
            # Get agent config
            agent_config = await self.agent_service.get_agent_config(company_id)

            # Create session
            session = self._get_or_create_session(call_sid, company_id)

            # Add greeting to history
            session.add_message("assistant", agent_config.greeting_message)

            # Synthesize greeting
            tts_audio, tts_format, tts_sample_rate = await self._synthesize_speech(
                text=agent_config.greeting_message,
                tts_provider=agent_config.tts_provider,
                tts_model=agent_config.tts_model,
                voice_id=agent_config.voice_id,
                voice_settings=agent_config.voice_settings,
                fallback_provider=agent_config.fallback_tts_provider
            )

            # Convert to Twilio format
            greeting_audio_base64 = self.audio_converter.tts_to_twilio_format(
                tts_audio,
                input_format=tts_format,
                input_sample_rate=tts_sample_rate if tts_format == "pcm" else None
            )

            logger.info(f"Generated greeting for call: {call_sid}")

            return greeting_audio_base64

        except Exception as e:
            logger.error(f"Error generating greeting: {str(e)}", exc_info=True)
            # Return empty on error (Twilio will handle silence)
            return ""


# Global singleton instance
# TODO: Consider dependency injection pattern for better testability
_voice_pipeline_service = None


def get_voice_pipeline_service() -> VoicePipelineService:
    """
    Get voice pipeline service singleton

    Returns:
        Voice pipeline service instance
    """
    global _voice_pipeline_service
    if _voice_pipeline_service is None:
        _voice_pipeline_service = VoicePipelineService()
    return _voice_pipeline_service


# Export service and types
__all__ = ["VoicePipelineService", "ConversationSession", "get_voice_pipeline_service"]
