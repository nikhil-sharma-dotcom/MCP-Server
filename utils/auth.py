from jose import jwt
from datetime import datetime, timedelta, UTC
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def create_token(username, role="admin"):
    expire = datetime.now(UTC) + timedelta(hours=1)
    payload={"sub": username,"role":role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)