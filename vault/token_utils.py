import hashlib
import uuid


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> tuple[str, str, str]:
    """Return (plaintext, hash, prefix[:8])."""
    plaintext = str(uuid.uuid4())
    token_hash = hash_token(plaintext)
    token_prefix = plaintext[:8]
    return plaintext, token_hash, token_prefix
