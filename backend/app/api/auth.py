from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.services.rbac_service import require_permission

from app.core.auth_dependencies import get_current_user,oauth2_scheme
from app.core.security import create_access_token,decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from app.services.auth_session_service import (
    create_auth_session,
    revoke_auth_session,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    database: Session = Depends(get_db),
):
    if get_user_by_username(
        database,
        user_data.username,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    if get_user_by_email(
        database,
        user_data.email,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    return create_user(
        database,
        user_data,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: LoginRequest,
    database: Session = Depends(get_db),
):
    user = authenticate_user(
        database,
        login_data.username,
        login_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    auth_session = create_auth_session(
        database,
        user.id,
    )

    token = create_access_token(
        str(user.id),
        auth_session.session_id,
    )

    return TokenResponse(
        access_token=token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user

@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    session_id = payload.get("sid")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication session",
        )

    revoked = revoke_auth_session(
        database,
        session_id,
    )

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session is no longer active",
        )

    return {
        "message": "Logged out successfully",
        "user": current_user.username,
    }

@router.get(
    "/security-test/account-balance",
)
def security_test_account_balance(
    current_user: User = Depends(
        require_permission(
            "account.balance.view"
        )
    ),
):
    return {
        "access": "granted",
        "user": current_user.username,
        "permission": "account.balance.view",
        "message": (
            "Permission passed. "
            "Data source execution would now be allowed."
        ),
    }