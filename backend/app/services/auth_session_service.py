from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_session import AuthSession


def create_auth_session(
    database: Session,
    user_id: int,
) -> AuthSession:
    session = AuthSession(
        session_id=uuid4().hex,
        user_id=user_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )

    database.add(session)
    database.commit()
    database.refresh(session)

    return session


def get_active_auth_session(
    database: Session,
    session_id: str,
) -> AuthSession | None:
    statement = (
        select(AuthSession)
        .where(
            AuthSession.session_id == session_id,
            AuthSession.is_active.is_(True),
        )
    )

    return database.scalar(statement)


def touch_auth_session(
    database: Session,
    session: AuthSession,
) -> None:
    session.last_seen_at = datetime.now(
        timezone.utc
    )

    database.commit()


def revoke_auth_session(
    database: Session,
    session_id: str,
) -> bool:
    session = get_active_auth_session(
        database,
        session_id,
    )

    if session is None:
        return False

    session.is_active = False
    session.revoked_at = datetime.now(
        timezone.utc
    )

    database.commit()

    return True


def revoke_all_user_sessions(
    database: Session,
    user_id: int,
) -> int:
    statement = (
        select(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.is_active.is_(True),
        )
    )

    sessions = list(
        database.scalars(statement).all()
    )

    now = datetime.now(timezone.utc)

    for session in sessions:
        session.is_active = False
        session.revoked_at = now

    if sessions:
        database.commit()

    return len(sessions)
