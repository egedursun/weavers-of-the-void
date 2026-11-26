import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from aerona.constants.providers import SECRET_HINT_LENGTH

OWNER_ONLY = 0o600


class SecretUnreadableError(Exception):
    pass


class SecretBox:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def seal(self, text: str) -> str:
        return self._fernet.encrypt(text.encode()).decode() if text else ""

    def open(self, sealed: str) -> str:
        if not sealed:
            return ""
        try:
            return self._fernet.decrypt(sealed.encode()).decode()
        except InvalidToken as error:
            raise SecretUnreadableError("a stored provider secret cannot be read with this server's secret key") from error


def hint_of(secret: str) -> str:
    return secret[-SECRET_HINT_LENGTH:] if len(secret) > SECRET_HINT_LENGTH * 2 else ""


def derived_key(phrase: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(phrase.encode()).digest())


def stored_key(file: Path) -> bytes:
    if file.exists():
        return file.read_bytes().strip()
    file.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    descriptor = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, OWNER_ONLY)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(key)
    return key


def secret_box(phrase: str, file: Path) -> SecretBox:
    return SecretBox(derived_key(phrase) if phrase else stored_key(file))
