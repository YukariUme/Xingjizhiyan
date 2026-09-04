"""语音服务统一接口：ASR（语音转文字）与 TTS（文字转语音）预留。

第一版提供 Mock 实现保证离线可用，后续可按 ASR_PROVIDER / TTS_PROVIDER
接入讯飞、Whisper、Azure 等真实服务，业务代码无需改动。
"""

import logging
import wave
from abc import ABC, abstractmethod
from io import BytesIO

from app.config import get_settings

logger = logging.getLogger(__name__)


class ASRError(RuntimeError):
    """语音识别调用失败统一异常。"""


class TTSError(RuntimeError):
    """语音合成调用失败统一异常。"""


class ASRService(ABC):
    """语音转文字服务接口。"""

    name: str = "base"

    @abstractmethod
    def transcribe_audio(self, audio_bytes: bytes, format: str = "wav") -> str:
        """输入音频字节，返回识别文本。"""
        raise NotImplementedError


class TTSService(ABC):
    """文字转语音服务接口。"""

    name: str = "base"

    @abstractmethod
    def synthesize_speech(self, text: str, voice: str = "") -> bytes:
        """输入文本，返回音频字节（wav/mp3）。"""
        raise NotImplementedError


class MockASRService(ASRService):
    """离线 Mock：返回固定识别文本（演示用）。"""

    name = "mock"

    def transcribe_audio(self, audio_bytes: bytes, format: str = "wav") -> str:
        size_kb = len(audio_bytes) // 1024
        return (
            f"（Mock 语音识别，音频约 {size_kb}KB）"
            "为什么生产者和消费者都需要使用信号量？"
        )


class MockTTSService(TTSService):
    """离线 Mock：生成一小段静音 wav（便于前端演示播放链路，不依赖外部服务）。"""

    name = "mock"

    def synthesize_speech(self, text: str, voice: str = "") -> bytes:
        buf = BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 8000)  # 0.5s 静音
        return buf.getvalue()


def get_asr_service() -> ASRService:
    """按 ASR_PROVIDER 创建语音识别服务（当前仅 mock）。"""
    provider = get_settings().asr_provider.lower()
    if provider != "mock":
        logger.warning("ASR_PROVIDER=%s 尚未接入，回退 Mock。", provider)
    return MockASRService()


def get_tts_service() -> TTSService:
    """按 TTS_PROVIDER 创建语音合成服务（当前仅 mock）。"""
    provider = get_settings().tts_provider.lower()
    if provider != "mock":
        logger.warning("TTS_PROVIDER=%s 尚未接入，回退 Mock。", provider)
    return MockTTSService()
