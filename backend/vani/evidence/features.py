"""Per-call features from AI summaries and turn transcripts."""
import re
from dataclasses import dataclass, field

from vani.domain.seller import BotCall, CallTurn
from vani.text.language import WORD, detect, english_share

# Tags read from VANI's AI call summaries (English prose). Calibrated on the real data.
SUMMARY_TAGS: dict[str, re.Pattern] = {k: re.compile(p, re.I) for k, p in {
    "busy": r"\bbusy\b|call (?:him |her |them )?(?:back )?later|\bdriving\b|in a meeting|not available|\boccupied\b|call back after",
    "confused": r"confus|did not understand|didn.t understand|unclear|misunderstand|asked (?:the agent )?to repeat",
    "frustrated": r"frustrat|irritat|annoy|\bangry\b|\brude\b|\bupset\b|too many calls|multiple calls",
    "bot_question": r"\bbot\b|robot|recorded|automated|real person|\bhuman\b",
    "language_issue": r"\blanguage\b|\benglish\b|\bhindi\b|\btamil\b|\btelugu\b|\bmarathi\b|\bgujarati\b|\bbengali\b|\bkannada\b|\bpunjabi\b",
    "price": r"\bprice|\bcost|\bcharge|\bfees?\b|\bpayment|\bmoney\b|\bpaid\b",
    "other_platform": r"tradeindia|justdial|alibaba|other platform|another platform",
    "already_in_touch": r"already (?:in touch|talked|spoke|spoken|has an executive|been contacted)|already (?:a )?(?:paid|customer)",
    "not_interested": r"not interested|no interest|declined|refused|no requirement",
    "whatsapp": r"whatsapp",
    "visit": r"\bvisit|\blocation\b|\baddress\b",
    "interest": r"(?<!not )(?<!no )(?<!un)\binterested\b|\bagreed\b|\bwilling\b|wanted to know|asked about",
}.items()}

EARLY_DROP_S = 20.0


@dataclass
class CallFeatures:
    attempt_id: str
    glid: str
    bot_version: str | None
    bucket: str | None
    duration_s: float | None
    meeting_fixed: bool
    disposition: str | None
    tags: set[str] = field(default_factory=set)
    early_drop: bool = False
    has_transcript: bool = False
    seller_language: str | None = None   # from transcript, if any
    seller_english_share: float | None = None
    seller_words_per_turn: float | None = None
    bot_words_first_turn: int | None = None


def summary_tags(summary: str | None) -> set[str]:
    if not summary:
        return set()
    return {tag for tag, p in SUMMARY_TAGS.items() if p.search(summary)}


def call_features(call: BotCall, turns: list[CallTurn]) -> CallFeatures:
    f = CallFeatures(
        attempt_id=call.attempt_id, glid=call.glid, bot_version=call.bot_version, bucket=call.bucket,
        duration_s=call.duration_s, meeting_fixed=call.meeting_fixed, disposition=call.disposition,
        tags=summary_tags(call.summary),
        early_drop=call.duration_s is not None and call.duration_s < EARLY_DROP_S,
    )
    seller = [t for t in turns if t.speaker == "seller" and t.text.strip()]
    bot = sorted((t for t in turns if t.speaker == "bot"), key=lambda t: t.turn_no)
    if turns:
        f.has_transcript = True
    if bot:
        f.bot_words_first_turn = len(WORD.findall(bot[0].text))
    if seller:
        votes: dict[str, float] = {}
        for t in seller:
            code, conf = detect(t.text)
            if conf >= 0.6:
                votes[code] = votes.get(code, 0.0) + len(WORD.findall(t.text)) * conf
        if votes:
            f.seller_language = max(votes, key=votes.get)
        joined = " ".join(t.text for t in seller)
        f.seller_english_share = english_share(joined)
        f.seller_words_per_turn = sum(len(WORD.findall(t.text)) for t in seller) / len(seller)
    return f
