"""Async Sarvam client: Saaras (STT), Bulbul (TTS), Sarvam LLM (chat).

Request/response shapes taken from Sarvam's official Python SDK (sarvamai 0.1.36):
  POST /speech-to-text        multipart: file, model=saaras:v3, mode=codemix, language_code=unknown
  POST /text-to-speech        json: text, language_code, speaker, pace, (pitch: v2 only), model
  POST /v1/chat/completions   json: OpenAI-style messages, model, reasoning_effort
Auth header: api-subscription-key.
"""
import asyncio
import logging
import re
from typing import Protocol

import httpx

from vani.config import Settings

log = logging.getLogger(__name__)
THINK = re.compile(r"<think>.*?</think>", re.S)


class SarvamError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class SpeechAI(Protocol):
    enabled: bool

    async def stt(self, audio: bytes, filename: str = "turn.wav", mode: str | None = None,
                  language: str | None = None) -> dict: ...
    async def tts(self, text: str, language_code: str, speaker: str, pace: float, pitch: float | None = None,
                  temperature: float | None = None) -> str: ...
    async def chat(self, messages: list[dict], max_tokens: int | None = None, model: str | None = None,
                   response_format: dict | None = None) -> str: ...


class SarvamClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.s = settings
        self.enabled = settings.sarvam_enabled
        self.http = httpx.AsyncClient(
            base_url=settings.sarvam_base_url, transport=transport,
            headers={"api-subscription-key": settings.sarvam_api_key},
            timeout=httpx.Timeout(settings.sarvam_timeout_s, connect=5.0),
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _post(self, path: str, retries: int = 1, **kw) -> dict:
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                r = await self.http.post(path, **kw)
            except httpx.HTTPError as exc:
                last = SarvamError(f"{path}: {exc.__class__.__name__}: {exc}")
            else:
                if r.status_code < 400:
                    return r.json()
                last = SarvamError(f"{path}: HTTP {r.status_code}: {r.text[:300]}", r.status_code)
                if r.status_code < 500 and r.status_code != 429:
                    break   # client errors won't fix themselves
            if attempt < retries:
                await asyncio.sleep(0.3 * (attempt + 1))
        raise last  # type: ignore[misc]

    async def stt(self, audio: bytes, filename: str = "turn.wav", mode: str | None = None,
                  language: str | None = None) -> dict:
        """language: a BCP-47 hint (gu-IN...) once the call is in a regional language; None = auto-detect."""
        data = await self._post(
            "/speech-to-text",
            files={"file": (filename, audio, "audio/wav")},
            data={"model": self.s.sarvam_stt_model, "mode": mode or self.s.sarvam_stt_mode,
                  "language_code": language or "unknown"},
        )
        return {"transcript": data.get("transcript", ""), "language_code": data.get("language_code"),
                "language_probability": data.get("language_probability")}

    async def tts(self, text: str, language_code: str, speaker: str, pace: float, pitch: float | None = None,
                  temperature: float | None = None) -> str:
        model = self.s.sarvam_tts_model
        body = {"text": text[:2400], "language_code": language_code, "speaker": speaker,
                "pace": max(0.5, min(2.0, pace)) if model != "bulbul:v2" else max(0.3, min(3.0, pace)),
                "model": model}
        if pitch is not None and model == "bulbul:v2":
            body["pitch"] = max(-0.75, min(0.75, pitch))
        if temperature is not None and model != "bulbul:v2":   # expressiveness: v3/v4 only
            body["temperature"] = max(0.01, min(1.0, temperature))
        try:
            data = await self._post("/text-to-speech", json=body)
        except SarvamError as exc:
            # Older API versions call the field target_language_code; retry once with that name.
            if exc.status in (400, 422) and "target_language_code" in str(exc):
                body["target_language_code"] = body.pop("language_code")
                data = await self._post("/text-to-speech", json=body)
            else:
                raise
        audios = data.get("audios") or []
        if not audios:
            raise SarvamError("/text-to-speech: no audio in response")
        return audios[0]

    async def chat(self, messages: list[dict], max_tokens: int | None = None, model: str | None = None,
                   response_format: dict | None = None) -> str:
        body = {"model": model or self.s.sarvam_chat_model, "messages": messages,
                "max_tokens": max_tokens or self.s.sarvam_chat_max_tokens,
                "temperature": 0.4, "reasoning_effort": "low"}
        if response_format:
            body["response_format"] = response_format   # structured outputs: json_schema / json_object
        data = await self._post("/v1/chat/completions", json=body)
        try:
            choice = data["choices"][0]
            msg = choice["message"]
            content = msg.get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise SarvamError(f"chat: unexpected response shape {str(data)[:200]}") from exc
        text = THINK.sub("", content).strip().strip('"').strip()
        if not text:
            # Reasoning models can spend the whole budget thinking and return no answer.
            reasoning = len(msg.get("reasoning_content") or "")
            raise SarvamError(f"chat: empty answer (finish_reason={choice.get('finish_reason')}, "
                              f"reasoning chars={reasoning})")
        return text


    async def transliterate(self, text: str, source: str, target: str, spoken_form: bool = False) -> str:
        """Change script, keep pronunciation ('how are you' -> 'हाउ आर यू'). spoken_form writes numbers as words."""
        data = await self._post("/transliterate", json={
            "input": text[:1000], "source_language_code": source, "target_language_code": target,
            "spoken_form": spoken_form, "numerals_format": "international"})
        out = data.get("transliterated_text")
        if not out:
            raise SarvamError("/transliterate: empty result")
        return out


    async def translate(self, text: str, target: str, source: str = "auto", speaker_gender: str | None = None,
                        mode: str = "modern-colloquial") -> str:
        """Sarvam Translate (Mayura). speaker_gender keeps Hindi verb forms right for the bot's voice."""
        body = {"input": text[:1000], "source_language_code": source, "target_language_code": target,
                "mode": mode, "model": "mayura:v1"}
        if speaker_gender in ("male", "female"):
            body["speaker_gender"] = speaker_gender.capitalize()
        data = await self._post("/translate", json=body)
        out = data.get("translated_text")
        if not out:
            raise SarvamError("/translate: empty result")
        return out


class OfflineSpeechAI:
    """No key / no network: the browser speaks and listens; replies come from templates."""
    enabled = False

    async def stt(self, audio, filename="turn.wav", mode=None, language=None):
        raise SarvamError("offline: send text instead of audio")

    async def tts(self, *a, **k):
        raise SarvamError("offline: no TTS")

    async def chat(self, *a, **k):
        raise SarvamError("offline: no LLM")

    async def transliterate(self, *a, **k):
        raise SarvamError("offline: no transliteration")

    async def translate(self, *a, **k):
        raise SarvamError("offline: no translation")
