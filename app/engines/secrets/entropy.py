import math
from collections import Counter


def shannon_entropy(data: str) -> float:
    """Calculate Shannon Entropy of a string to measure randomness/character diversity.

    Typical high-entropy values:
    - Random 32-char hex string: ~3.8 to 4.0
    - Base64 random token: > 4.2
    - Standard English prose: ~2.5 to 3.2
    """
    if not data:
        return 0.0

    length = len(data)
    counts = Counter(data)
    entropy = 0.0

    for count in counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return round(entropy, 4)
