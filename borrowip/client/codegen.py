"""Generate connection codes."""

import random
import string


def generate_code() -> str:
    """Generate BIP-xxxxxx connection code."""
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"BIP-{suffix}"
