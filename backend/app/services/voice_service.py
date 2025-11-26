import asyncio
import os
import uuid
from typing import Optional, Tuple

from faster_whisper import WhisperModel
import pyttsx3

from config import settings


class VoiceService:
    """Local speech-to-text and text-to-speech utilities."""

    def __init__(self):
        self.audio_dir = settings.absolute_audio_dir
        os.makedirs(self.audio_dir, exist_ok=True)
        self.device, self.compute_type = self._detect_device()
        self.whisper_model = WhisperModel(
            settings.whisper_model,
            device=self.device,
            compute_type=self.compute_type,
        )

    def _detect_device(self) -> Tuple[str, str]:
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda", "float16"
        except Exception:
            pass
        return "cpu", "int8"

    async def transcribe(self, file_path: str, language: Optional[str] = None):
        def _run_transcription():
            segments, info = self.whisper_model.transcribe(
                file_path,
                language=language,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return text, info.language, getattr(info, "duration", None)

        return await asyncio.to_thread(_run_transcription)

    async def synthesize(self, text: str, voice: Optional[str] = None) -> str:
        output_path = os.path.join(self.audio_dir, f"{uuid.uuid4()}.wav")

        def _run_tts():
            engine = pyttsx3.init()
            if voice:
                engine.setProperty("voice", voice)
            engine.save_to_file(text, output_path)
            engine.runAndWait()

        await asyncio.to_thread(_run_tts)
        return output_path

    def cleanup_audio(self, path: str):
        if path and os.path.exists(path):
            os.remove(path)


voice_service = VoiceService()

