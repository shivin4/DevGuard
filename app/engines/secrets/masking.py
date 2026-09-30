def mask_secret(secret: str) -> str:
    """Mask sensitive value so that only non-sensitive prefix and suffix remain visible.

    Guarantees that sensitive content is obfuscated before logging, storage, or LLM submission.
    Examples:
    - 'AKIA1234567890ABCDEF' -> 'AKIA****CDEF'
    - 'ghp_1234567890abcdef' -> 'ghp_****cdef'
    - 'secret' -> 's****t'
    """
    if not secret:
        return "****"

    length = len(secret)
    if length <= 4:
        return "****"
    elif length <= 8:
        return f"{secret[0]}****{secret[-1]}"
    else:
        prefix_len = 4
        suffix_len = 4
        return f"{secret[:prefix_len]}****{secret[-suffix_len:]}"
