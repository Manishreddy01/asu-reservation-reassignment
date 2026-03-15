"""
Prototype security helpers.

Uses a Base64-encoded mock token instead of real JWT.
To upgrade to production auth, replace `create_mock_token` / `decode_mock_token`
with a proper JWT library and update `get_current_user` to validate the signature.
Everything else (route handlers, schemas) stays the same.
"""

import base64

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Mock token (prototype only)
# Encodes "user_id:email" as Base64.  Not signed — replace with JWT for prod.
# ---------------------------------------------------------------------------
def create_mock_token(user_id: int, email: str) -> str:
    payload = f"{user_id}:{email}"
    return base64.b64encode(payload.encode()).decode()


def decode_mock_token(token: str) -> int | None:
    """Return user_id from token, or None if malformed."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        user_id_str, _ = decoded.split(":", 1)
        return int(user_id_str)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# FastAPI auth dependency
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolves the authenticated user from the Bearer token.
    Swap the token-decoding logic here when upgrading to real JWT/SSO.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
        )

    user_id = decode_mock_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token references a user that no longer exists.",
        )

    return user
