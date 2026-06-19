import base64
import hashlib

from cryptography.fernet import Fernet

from ..config import settings


def _derive_key() -> bytes:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest[:32])


_fernet = Fernet(_derive_key())


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]
