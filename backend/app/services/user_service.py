from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.entities import User
from app.schemas.entities import UserCreate, UserUpdate
from app.core.security import hash_password, verify_password, create_access_token


class UserService:
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.scalar(select(User).where(User.email == email.lower().strip()))

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.scalar(select(User).where(User.id == user_id))

    @staticmethod
    def register(db: Session, user_in: UserCreate) -> User:
        """
        Registers a new student account.
        Enforces unique email and Argon2 password hashing.
        """
        existing = UserService.get_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name.strip(),
            program=user_in.program.strip() if user_in.program else "B.Tech Computer Science & AI",
            semester=user_in.semester.strip() if user_in.semester else "Semester 6",
            avatar_url=user_in.avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User:
        """
        Authenticates user credentials against the stored Argon2 hash.
        """
        user = UserService.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account.",
            )

        return user

    @staticmethod
    def update_profile(db: Session, user: User, update_in: UserUpdate) -> User:
        """
        Updates safe user profile fields.
        Excludes ID, password_hash, or email modification from this endpoint.
        """
        update_data = update_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user


user_service = UserService()
