"""Undo a doubled transcript ("bahut bahut saari saari ke ke meeting meeting").

People do repeat words ("haan haan", "jaldi jaldi"), so a few repeats are kept.
Only when most words are immediately repeated is it an audio problem (the same
audio sent twice), and then every immediate repeat is collapsed.
"""

STUTTER_SHARE = 0.35   # share of distinct spoken words that came out doubled


def collapse_doubled(text: str) -> tuple[str, bool]:
    words = (text or "").split()
    if len(words) < 6:
        return text, False
    norm = [w.lower().strip(",.?!।") for w in words]
    repeats = sum(1 for a, b in zip(norm, norm[1:]) if a == b)
    if repeats / (len(words) - repeats) < STUTTER_SHARE:
        return text, False
    out = [words[0]]
    for prev, w, n in zip(norm, words[1:], norm[1:]):
        if n != prev:
            out.append(w)
    return " ".join(out), True
