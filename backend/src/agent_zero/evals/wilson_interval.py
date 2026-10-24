from math import sqrt

Z_95 = 1.959964


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float] | None:
    if total <= 0:
        return None
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z * sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)
