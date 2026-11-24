from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import UserCreate, UserResponse
from app.schemas.auth import Token, LoginRequest
from app.services.user_service import user_service
from app.core.security import create_access_token

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new student account:
    - Validates email format and password length
    - Rejects duplicate email addresses
    - Hashes password using Argon2id
    - Returns safe UserResponse without exposing password hash
    """
    user = user_service.register(db, user_in)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and obtain JWT access token (JSON)",
)
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates student credentials via JSON:
    - Verifies password against Argon2 hash
    - Emits standard OAuth2-compatible JWT access token
    - Returns token and safe user profile
    """
    user = user_service.authenticate(db, login_in.email, login_in.password)
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 compatible token login (Swagger UI / OAuth2 form)",
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2-compliant token endpoint:
    - Accepts application/x-www-form-urlencoded form data (username, password)
    - Directly enables Swagger UI's 'Authorize' button authentication
    - Authenticates student using UserService with username mapped to email
    - Emits standard JWT access token and safe user profile
    """
    user = user_service.authenticate(db, form_data.username, form_data.password)
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get currently authenticated user's profile",
)
def get_auth_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated student profile using JWT credentials.
    """
    return current_user
