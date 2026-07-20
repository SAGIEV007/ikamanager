"""Encryption utilities for storing sensitive data."""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import get_settings


def _get_fernet() -> Fernet:
    """Get Fernet cipher using the app encryption key."""
    settings = get_settings()
    key = settings.encryption_key.encode()

    # Derive a proper 32-byte key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ikamanager-salt-v1",
        iterations=100000,
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(key))
    return Fernet(derived_key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password for storage."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
