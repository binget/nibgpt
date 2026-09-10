from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_username(
    database: Session,
    username: str,
) -> User | None:
    statement = select(User).where(User.username == username)
    return database.scalar(statement)


def get_user_by_email(
    database: Session,
    email: str,
) -> User | None:
    statement = select(User).where(User.email == email)
    return database.scalar(statement)


def get_user_by_login(
    database: Session,
    login_value: str,
) -> User | None:
    statement = select(User).where(
        or_(
            User.username == login_value,
            User.email == login_value,
        )
    )

    return database.scalar(statement)


def create_user(
    database: Session,
    user_data: UserCreate,
) -> User:
    user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role="user",
    )

    database.add(user)
    database.commit()
    database.refresh(user)

    return user


def authenticate_user(
    database: Session,
    login_value: str,
    password: str,
) -> User | None:
    user = get_user_by_login(database, login_value)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
