"""What the best sellers in the same category get from IndiaMART: a true, positive benefit to quote.

From the seller table: per category group (>= 30 sellers), the 90th-percentile
enquiries and buyer calls in 90 days. "Top sellers in your category get 12+
enquiries in three months; you got 2" is honest (real numbers), positive (it's
what's possible) and personal (their own gap). No invented "lots of buyers".
"""
from collections import defaultdict
from typing import Iterable

from vani.domain.seller import SellerProfile

MIN_SELLERS = 30


def _p90(xs: list[float]) -> int:
    xs = sorted(xs)
    return int(round(xs[min(len(xs) - 1, int(len(xs) * 0.9))])) if xs else 0


class CategoryDemand:
    def __init__(self, groups: dict[str, dict]):
        self.groups = groups

    @classmethod
    def build(cls, profiles: Iterable[SellerProfile]) -> "CategoryDemand":
        enq, calls = defaultdict(list), defaultdict(list)
        for p in profiles:
            if not p.category_group:
                continue
            if p.engagement.enquiries_90d is not None:
                enq[p.category_group].append(p.engagement.enquiries_90d)
            if p.engagement.buyer_calls_90d is not None:
                calls[p.category_group].append(p.engagement.buyer_calls_90d)
        groups = {g: {"sellers": len(v), "top_enquiries_90d": _p90(v), "top_buyer_calls_90d": _p90(calls[g])}
                  for g, v in enq.items() if len(v) >= MIN_SELLERS}
        every = [x for v in enq.values() for x in v]
        groups[""] = {"sellers": len(every), "top_enquiries_90d": _p90(every),
                      "top_buyer_calls_90d": _p90([x for v in calls.values() for x in v])}
        return cls(groups)

    @classmethod
    def empty(cls) -> "CategoryDemand":
        return cls({})

    def facts(self, p: SellerProfile) -> dict:
        """Numbers VANI may say for this seller (own + category top 10%), nothing else."""
        scope = "category" if (p.category_group or "") in self.groups and p.category_group else "all"
        g = self.groups.get(p.category_group or "") if scope == "category" else self.groups.get("")
        own = p.engagement.enquiries_90d
        out = {"category": p.categories[0] if p.categories else None,
               "own_enquiries_90d": None if own is None else int(own)}
        if g and g["top_enquiries_90d"] >= 3:
            out.update(top_enquiries_90d=g["top_enquiries_90d"], top_buyer_calls_90d=g["top_buyer_calls_90d"],
                       peer_sellers=g["sellers"], scope=scope)
        return out


def benefit_line(style: str, f: dict) -> str:
    """One positive, true sentence about what IndiaMART can add for THIS seller."""
    top, own = f.get("top_enquiries_90d"), f.get("own_enquiries_90d")
    calls = f.get("top_buyer_calls_90d") or 0
    mine = f.get("scope", "category") == "category"
    gap = own is not None and top is not None and own < top
    if style == "english":
        if top:
            s = ("Top sellers in your category" if mine else "Top sellers on IndiaMART") + f" get over {top} enquiries" + (f" and {calls} buyer calls" if calls >= 3 else "") + " in three months"
            return s + (f"; you got {own}, and a better listing closes that gap." if gap else ", and a better listing gets you there.")
        if own:
            return f"You got {own} enquiries in the last three months; a better listing brings more."
        return "A good listing puts your products in front of the right buyers, and that brings enquiries."
    if style == "gujarati":
        if top:
            s = ("તમારી category ના ટોપ sellers ને" if mine else "IndiaMART ના ટોપ sellers ને") + f" ત્રણ મહિનામાં {top} થી વધારે enquiries" + (f" અને {calls} buyer calls" if calls >= 3 else "") + " મળે છે"
            return s + (f"; તમને {own} મળી, listing સરખી થવાથી આ ફરક ઘટે છે." if gap else ", listing સરખી થવાથી તમે પણ ત્યાં પહોંચી શકો.")
        if own:
            return f"તમને છેલ્લા ત્રણ મહિનામાં {own} enquiries મળી છે, listing સારી થવાથી વધારે આવશે."
        return "સારી listing થી તમારા products સાચા buyers સુધી પહોંચે છે અને enquiries આવે છે."
    if top:
        s = ("आपकी category के top sellers को" if mine else "IndiaMART के top sellers को") + f" तीन महीने में {top} से ज़्यादा enquiries" + (f" और {calls} buyer calls" if calls >= 3 else "") + " मिलती हैं"
        return s + (f", आपको अभी {own} {'मिली' if own == 1 else 'मिलीं'}, listing ठीक होने से यही फ़र्क कम होता है।" if gap else ", listing अच्छी होने से आप भी वहाँ पहुँच सकते हैं।")
    if own:
        return f"आपको पिछले तीन महीने में {own} enquiries आई हैं, listing बेहतर होने से और ज़्यादा आएँगी।"
    return "Listing अच्छी होने से आपके products सही buyers तक पहुँचते हैं और enquiries बढ़ती हैं।"
