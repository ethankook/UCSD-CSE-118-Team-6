# asr_service.py
import base64
import os
import tempfile
from typing import Optional

import whisper


def map_app_lang_to_whisper(app_lang: Optional[str]) -> Optional[str]:
    """
    Map app-level language codes (en, en-us, es-419, zh-hans, etc.)
    to a language string Whisper understands (usually 2-letter ISO).
    Returns None to let Whisper auto-detect.
    """
    if not app_lang:
        return None

    norm = app_lang.lower()

    # English
    if norm in {"en", "en-us", "en-gb"}:
        return "en"

    # Spanish
    if norm in {"es", "es-419"}:
        return "es"

    # Portuguese
    if norm in {"pt", "pt-br", "pt-pt"}:
        return "pt"

    # Chinese
    if norm in {"zh", "zh-hans", "zh-hant"}:
        return "zh"

    # Fallback: first two letters (fr-ca -> fr, de-at -> de, etc.)
    return norm[:2]


class AsrService:
    """
    Backend ASR using local Whisper.

    - Expects base64-encoded WAV from headset.
    - Runs Whisper on the server.
    - Returns recognized text.
    """

    def __init__(self, model_name: str = "tiny"):
        print(f"[ASR] Loading Whisper model: {model_name}")
        self.model = whisper.load_model(model_name)
        print("[ASR] Whisper model loaded")

    def transcribe_wav_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language_hint: Optional[str] = None,
    ) -> str:
        """
        :param audio_bytes: raw WAV bytes (16kHz mono PCM recommended)
        :param sample_rate: not strictly needed if the WAV header is correct
        :param language_hint: app-level code ("en", "es-419", etc.)
        :return: recognized text
        """
        whisper_lang = map_app_lang_to_whisper(language_hint)

        # Whisper transcribe works easiest on a file path.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = self.model.transcribe(
                tmp_path,
                fp16=False,            # CPU-friendly
                language=whisper_lang  # or None for auto-detect
            )
            text = (result.get("text") or "").strip()
            return text
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def transcribe_b64_wav(
        self,
        audio_b64: str,
        sample_rate: int = 16000,
        language_hint: Optional[str] = None,
    ) -> str:
        """
        Take base64-encoded WAV and return transcript text.
        """
        audio_bytes = base64.b64decode(audio_b64)
        return self.transcribe_wav_bytes(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
            language_hint=language_hint,
        )
