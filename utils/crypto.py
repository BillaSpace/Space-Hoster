"""
Auto-managed encryption key.
Key is generated on first run (encryption.key) so the owner never
needs to set it manually.  Users never see the key.
"""
import os, base64, pathlib
from cryptography.fernet import Fernet

_KEY_FILE = "encryption.key"

def _get_fernet() -> Fernet:
    if not os.path.exists(_KEY_FILE):
        key = Fernet.generate_key()
        pathlib.Path(_KEY_FILE).write_bytes(key)
    else:
        key = pathlib.Path(_KEY_FILE).read_bytes()
    return Fernet(key)

def encrypt(text: str) -> str:
    f = _get_fernet()
    return base64.b64encode(f.encrypt(text.encode())).decode()

def decrypt(token_b64: str) -> str:
    f = _get_fernet()
    return f.decrypt(base64.b64decode(token_b64.encode())).decode()
