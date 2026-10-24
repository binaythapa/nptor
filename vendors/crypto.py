import base64
import hashlib
import logging
import os
from typing import List

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

logger = logging.getLogger(__name__)


class BankCryptoError(Exception):
    """Base exception for banking crypto operations."""
    pass


class DecryptionError(BankCryptoError):
    """Raised when bank account ciphertext cannot be decrypted by any configured key."""
    pass


class KeyConfigurationError(BankCryptoError):
    """Raised when encryption keys are missing or malformed."""
    pass


def get_encryption_keys() -> List[bytes]:
    """
    Returns a list of 32-byte url-safe base64-encoded keys for Fernet AES encryption.
    Primary key is index 0. Subsequent keys are historical keys for rotation fallback.
    Configured via BANK_DETAILS_ENCRYPTION_KEY or BANK_DETAILS_ENCRYPTION_KEYS (comma-separated).
    Fallback (development only): Derived from settings.SECRET_KEY.
    """
    env_keys = (
        os.environ.get("BANK_DETAILS_ENCRYPTION_KEYS")
        or os.environ.get("BANK_DETAILS_ENCRYPTION_KEY")
        or os.environ.get("STORE_BANK_ENCRYPTION_KEY")
    )
    if env_keys:
        keys = [k.strip().encode("utf-8") for k in env_keys.split(",") if k.strip()]
        if keys:
            for k in keys:
                try:
                    Fernet(k)
                except Exception as exc:
                    raise KeyConfigurationError(f"Configured key is not a valid 32-byte Fernet key: {exc}") from exc
            return keys

    # Deterministic fallback derivation from SECRET_KEY (development only)
    if not getattr(settings, "SECRET_KEY", None):
        raise KeyConfigurationError("Neither BANK_DETAILS_ENCRYPTION_KEY nor settings.SECRET_KEY is configured.")
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest())
    return [derived]


def get_cipher() -> MultiFernet:
    keys = get_encryption_keys()
    fernets = [Fernet(k) for k in keys]
    return MultiFernet(fernets)


def encrypt_bank_account(plaintext: str) -> str:
    """
    Encrypt a plaintext bank account string into base64 ciphertext using the primary key.
    Never logs plaintext bank account.
    """
    if not plaintext:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_bank_account(ciphertext: str) -> str:
    """
    Decrypt base64 ciphertext back into a plaintext bank account string.
    Tries each configured key in MultiFernet order (primary first, then rotation fallbacks).
    Never logs decrypted account number.
    Raises DecryptionError if token is invalid or no key matches.
    """
    if not ciphertext:
        return ""
    cipher = get_cipher()
    try:
        return cipher.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Failed to decrypt bank account ciphertext: invalid token or mismatched key.")
        raise DecryptionError("Unable to decrypt bank details. Check configured encryption keys.") from exc
    except Exception as exc:
        logger.error("Unexpected error during bank account decryption.")
        raise DecryptionError("Unexpected bank details decryption error.") from exc


def rotate_bank_account_ciphertext(ciphertext: str) -> str:
    """
    Re-encrypts ciphertext that was encrypted with an older fallback key
    so that it is now encrypted with the current primary key.
    Raises DecryptionError if the ciphertext cannot be decrypted.
    """
    if not ciphertext:
        return ""
    cipher = get_cipher()
    try:
        rotated = cipher.rotate(ciphertext.encode("ascii"))
        return rotated.decode("ascii")
    except InvalidToken as exc:
        raise DecryptionError("Unable to rotate bank details ciphertext. Invalid token.") from exc
