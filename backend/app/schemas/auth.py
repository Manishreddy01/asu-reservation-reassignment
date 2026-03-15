from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole


class LoginResponse(BaseModel):
    user: UserOut
    mock_token: str
    token_type: str = "bearer"
    note: str = "Prototype token only — replace with real JWT/SSO for production."
