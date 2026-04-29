import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes:
    raw = os.environ.get("LOCKER_ENCRYPTION_KEY")
    if not raw:
        raise RuntimeError("LOCKER_ENCRYPTION_KEY is not set")
    return base64.b64decode(raw)


def encrypt(plaintext: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    blob = nonce + ciphertext
    return base64.b64encode(blob).decode()


def decrypt(blob_b64: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    blob = base64.b64decode(blob_b64)
    nonce = blob[:12]
    ciphertext = blob[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()
