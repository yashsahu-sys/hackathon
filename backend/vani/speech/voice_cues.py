"""How the seller SOUNDS, not just what they say: speaking rate and loudness from the turn's audio.

Saaras gives us words; the WAV gives us time and energy. Words per voiced second
tells a fast talker from a slow one, and loudness relative to the seller's own
first turns tells a raised voice. Thresholds come from real VANI calls: seller
turns run at 2.6 words/s (median of 279 sellers with timed turns; p15 ~1.8,
p85 ~3.4), so we only react at the edges, where a human caller would notice.
"""
import io
import math
import wave
from array import array
from dataclasses import dataclass

FAST_WPS = 3.4      # ~85th percentile of real seller turns
SLOW_WPS = 1.8      # ~15th percentile
LOUD_DB = 6.0       # this much above the seller's own baseline = raised voice
MIN_WORDS = 4       # rate on 1-3 words is noise
FRAME_S = 0.03


@dataclass
class VoiceCues:
    duration_s: float
    voiced_s: float
    words: int
    words_per_s: float | None
    rms_db: float
    band: str            # fast / normal / slow / unknown

    def as_dict(self) -> dict:
        return {"duration_s": round(self.duration_s, 2), "voiced_s": round(self.voiced_s, 2), "words": self.words,
                "words_per_s": None if self.words_per_s is None else round(self.words_per_s, 2),
                "rms_db": round(self.rms_db, 1), "band": self.band}


def _db(x: float) -> float:
    return 20 * math.log10(max(x, 1e-6) / 32768)


def analyze(audio: bytes, transcript: str) -> VoiceCues | None:
    """Cues from a 16-bit PCM WAV turn, or None for anything else (compressed audio, empty, broken)."""
    try:
        with wave.open(io.BytesIO(audio)) as w:
            if w.getsampwidth() != 2 or w.getnframes() == 0:
                return None
            rate, ch = w.getframerate(), w.getnchannels()
            samples = array("h", w.readframes(w.getnframes()))
    except (wave.Error, EOFError, ValueError):
        return None
    if ch > 1:
        samples = samples[::ch]
    n = max(1, int(rate * FRAME_S))
    frames = [samples[i:i + n] for i in range(0, len(samples) - n + 1, n)]
    if not frames:
        return None
    rms = [math.sqrt(sum(s * s for s in f) / len(f)) for f in frames]
    floor = sorted(rms)[len(rms) // 10]                 # quietest 10% = background
    thr = max(floor * 3, 300)                           # speech is well above the noise floor
    voiced = [r for r in rms if r > thr]
    voiced_s = len(voiced) * FRAME_S
    words = len((transcript or "").split())
    wps = words / voiced_s if voiced_s >= 0.6 and words >= MIN_WORDS else None
    band = "unknown" if wps is None else "fast" if wps >= FAST_WPS else "slow" if wps <= SLOW_WPS else "normal"
    level = _db(sum(voiced) / len(voiced)) if voiced else _db(floor)
    return VoiceCues(len(samples) / rate, voiced_s, words, wps, level, band)


def raised(level_db: float, baseline: list[float]) -> bool:
    """Louder than this seller's own first turns (mic distance differs per seller, so never absolute)."""
    if len(baseline) < 1:
        return False
    return level_db - sorted(baseline)[len(baseline) // 2] >= LOUD_DB
