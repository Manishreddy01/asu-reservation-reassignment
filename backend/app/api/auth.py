from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_mock_token, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Student login",
    description=(
        "Verify email and password against seeded user accounts. "
        "Returns user info and a prototype Bearer token for subsequent requests. "
        "Replace token logic with real JWT/SSO when moving to production."
    ),
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_mock_token(user.id, user.email)
    return LoginResponse(user=UserOut.model_validate(user), mock_token=token)
