import hashlib
import random
import string
import uuid


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> tuple[str, str, str]:
    """Return (plaintext, hash, prefix[:8])."""
    plaintext = str(uuid.uuid4())
    token_hash = hash_token(plaintext)
    token_prefix = plaintext[:8]
    return plaintext, token_hash, token_prefix


def generate_invite_code(name: str) -> str:
    """Generate a short invite code like ACME-7X3K from a team name."""
    alpha = "".join(c for c in name.upper() if c.isalpha())[:4]
    if len(alpha) < 4:
        alpha = alpha.ljust(4, "X")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{alpha}-{suffix}"


def generate_pat() -> tuple[str, str, str]:
    """Return (plaintext, hash, prefix[:8]). Prefixed with pat_ for clarity."""
    plaintext = "pat_" + uuid.uuid4().hex
    token_hash = hash_token(plaintext)
    token_prefix = plaintext[:8]
    return plaintext, token_hash, token_prefix
