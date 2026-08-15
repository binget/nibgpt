from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


cipher = Fernet(
    settings.data_source_encryption_key.encode()
)


def encrypt_value(value: str) -> str:
    return cipher.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    try:
        return cipher.decrypt(value.encode()).decode()
    except InvalidToken as error:
        raise ValueError("Unable to decrypt stored credential") from error
