import os
import base64
from jose import jwt
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Load .env file
env_path = Path(__file__).resolve().parent / ".env.prod"
load_dotenv(env_path)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Make sure SECRET_KEY is converted to bytes for cryptography
SECRET_KEY_BYTES = SECRET_KEY.encode("utf-8")

# Derive a proper 32-byte AES key from SECRET_KEY
def derive_aes_key(secret: bytes) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = AES-256
        salt=None,  
        info=b"jwt-encryption",
        backend=default_backend(),
    )
    return hkdf.derive(secret)

AES_KEY = derive_aes_key(SECRET_KEY_BYTES)  # ✅ AES_KEY is now bytes

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    jwt_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Step 2: Encrypt JWT with AES-GCM
    aesgcm = AESGCM(AES_KEY)
    iv = os.urandom(12)  # 96-bit nonce for AES-GCM
    salt = os.urandom(16)  # extra salt
    encrypted = aesgcm.encrypt(iv, jwt_token.encode(), salt)

    # Step 3: Return base64 encoded token (iv + salt + ciphertext)
    token_bytes = iv + salt + encrypted
    return base64.urlsafe_b64encode(token_bytes).decode()

def decode_access_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])