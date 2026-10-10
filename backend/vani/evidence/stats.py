"""Small, dependency-free statistics used by the evidence miner."""
import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0 if k1 / n1 == k2 / n2 else 0.0
    z = abs(k1 / n1 - k2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def strength(p: float, n_small: int, n_tests: int = 1) -> str:
    """Bonferroni-adjusted p plus a sample-size floor. Matches domain Confidence values."""
    p_adj = min(1.0, p * max(1, n_tests))
    if n_small < 30:
        return "weak"
    if p_adj < 0.01 and n_small >= 100:
        return "strong"
    if p_adj < 0.05:
        return "moderate"
    return "weak"
