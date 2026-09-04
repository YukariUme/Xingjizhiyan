"""语音抽象层：ASR / TTS 预留接口与 Mock 实现。"""

from app.services.voice.base import (
    ASRError,
    ASRService,
    MockASRService,
    MockTTSService,
    TTSError,
    TTSService,
    get_asr_service,
    get_tts_service,
)

__all__ = [
    "ASRService",
    "TTSService",
    "MockASRService",
    "MockTTSService",
    "ASRError",
    "TTSError",
    "get_asr_service",
    "get_tts_service",
]
