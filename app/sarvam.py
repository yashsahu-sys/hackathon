"""Thin Sarvam REST client: Saaras (STT), Bulbul (TTS), Sarvam LLM (chat)."""
import re

import httpx

from . import config


class SarvamError(RuntimeError):
    pass


class SarvamClient:
    def __init__(self, api_key: str = config.SARVAM_API_KEY, base_url: str = config.SARVAM_BASE_URL):
        self.api_key = api_key
        self.http = httpx.Client(
            base_url=base_url,
            headers={"api-subscription-key": api_key},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _post(self, path: str, **kwargs) -> dict:
        try:
            resp = self.http.post(path, **kwargs)
        except httpx.HTTPError as exc:
            raise SarvamError(f"{path}: {exc}") from exc
        if resp.status_code >= 400:
            raise SarvamError(f"{path}: HTTP {resp.status_code} {resp.text[:300]}")
        return resp.json()

    def stt(self, audio: bytes, filename: str = "turn.wav") -> dict:
        """Returns {"transcript": str, "language_code": str|None}."""
        data = self._post(
            "/speech-to-text",
            files={"file": (filename, audio, "audio/wav")},
            # codemix keeps Hinglish as Hinglish ("मेरा phone number है")
            data={"model": config.STT_MODEL, "mode": "codemix", "language_code": "unknown"},
        )
        return {"transcript": data.get("transcript", ""), "language_code": data.get("language_code")}

    def tts(self, text: str, language_code: str, speaker: str, pace: float, temperature: float = 0.6) -> str:
        """Returns base64 WAV."""
        data = self._post(
            "/text-to-speech",
            json={
                "text": text[:2400],
                "language_code": language_code,
                "speaker": speaker,
                "pace": max(0.5, min(2.0, pace)),
                "temperature": temperature,
                "model": config.TTS_MODEL,
            },
        )
        audios = data.get("audios") or []
        if not audios:
            raise SarvamError("/text-to-speech: empty audio")
        return audios[0]

    def chat(self, messages: list[dict], max_tokens: int = 300, temperature: float = 0.5) -> str:
        data = self._post(
            "/v1/chat/completions",
            json={
                "model": config.CHAT_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "reasoning_effort": "low",
            },
        )
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise SarvamError(f"chat: unexpected response {str(data)[:300]}") from exc
        return strip_reasoning(content)


def strip_reasoning(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return text.strip().strip('"').strip()
