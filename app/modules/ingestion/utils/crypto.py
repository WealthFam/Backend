import base64
import hashlib
from cryptography.fernet import Fernet
from backend.app.core.config import settings

class CryptoUtils:
    _fernet = None

    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            # Derive a 32-byte key from the SECRET_KEY for Fernet
            key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
            cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not plaintext:
            return ""
        f = cls._get_fernet()
        return f.encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            f = cls._get_fernet()
            return f.decrypt(ciphertext.encode()).decode()
        except Exception:
            # If decryption fails (e.g. invalid key or non-encrypted data), return as is for backward compatibility
            return ciphertext
