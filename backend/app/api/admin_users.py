from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)
from sqlalchemy import (
    delete,
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import get_db
from app.models.rbac import (
    Role,
    UserDataScope,
    UserRole,
)
from app.models.user import User
from app.services.rbac_service import (
    require_permission,
)


router = APIRouter(
    prefix="/api/admin/users",
    tags=["NIBGPT Administration - Users"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class UserScopeInput(BaseModel):
    scope_type: Literal[
        "enterprise",
        "department",
        "branch",
        "self",
    ]

    scope_value: str | None = Field(
        default=None,
        max_length=150,
    )


class AdminUserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
    )

    full_name: str = Field(
        min_length=2,
        max_length=150,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role_id: int

    scopes: list[UserScopeInput] = []


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    email: EmailStr | None = None

    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )

    role_id: int | None = None

    scopes: list[UserScopeInput] | None = None


class UserStatusUpdate(BaseModel):
    is_active: bool
    
    
# ============================================================
# UPDATE USER
# ============================================================


@router.put("/{user_id}")
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.users.manage"
        )
    ),
):
    user = database.get(
        User,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.email is not None:
        email = str(
            payload.email
        ).lower()

        duplicate = database.scalar(
            select(User)
            .where(
                User.email == email,
                User.id != user.id,
            )
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        user.email = email

    if payload.full_name is not None:
        user.full_name = (
            payload.full_name.strip()
        )

    if payload.password is not None:
        user.hashed_password = (
            hash_password(
                payload.password
            )
        )

    # ----------------------------------------------
    # Replace role
    # ----------------------------------------------

    if payload.role_id is not None:

        role = database.scalar(
            select(Role)
            .where(
                Role.id == payload.role_id,
                Role.is_active.is_(True),
            )
        )

        if role is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected role does not exist "
                    "or is inactive"
                ),
            )

        database.execute(
            delete(UserRole)
            .where(
                UserRole.user_id
                == user.id
            )
        )

        database.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
            )
        )

    # ----------------------------------------------
    # Replace scopes
    # ----------------------------------------------

    if payload.scopes is not None:

        for scope in payload.scopes:

            if (
                scope.scope_type
                == "enterprise"
                and scope.scope_value
                not in {None, ""}
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Enterprise scope must "
                        "not contain a scope value"
                    ),
                )

            if (
                scope.scope_type
                in {"department", "branch"}
                and not (
                    scope.scope_value
                    and
                    scope.scope_value.strip()
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{scope.scope_type.title()} "
                        "scope requires a value"
                    ),
                )

        database.execute(
            delete(UserDataScope)
            .where(
                UserDataScope.user_id
                == user.id
            )
        )

        for scope in payload.scopes:

            scope_value = (
                scope.scope_value.strip()
                if scope.scope_value
                else None
            )

            database.add(
                UserDataScope(
                    user_id=user.id,
                    scope_type=(
                        scope.scope_type
                    ),
                    scope_value=scope_value,
                    is_active=True,
                )
            )

    database.commit()
    database.refresh(user)

    return {
        "message": (
            "User updated successfully"
        ),
        "data": serialize_user(
            database,
            user,
        ),
    }


# ============================================================
# ACTIVATE / DISABLE USER
# ============================================================


@router.patch("/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    database: Session = Depends(get_db),
    current_admin: User = Depends(
        require_permission(
            "admin.users.manage"
        )
    ),
):
    user = database.get(
        User,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent an administrator from accidentally
    # disabling the account currently being used.
    if (
        user.id == current_admin.id
        and not payload.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You cannot disable your own "
                "administrator account"
            ),
        )

    user.is_active = (
        payload.is_active
    )

    database.commit()
    database.refresh(user)

    return {
        "message": (
            "User activated successfully"
            if user.is_active
            else "User disabled successfully"
        ),
        "data": serialize_user(
            database,
            user,
        ),
    }

# ============================================================
# HELPERS
# ============================================================


def serialize_user(
    database: Session,
    user: User,
) -> dict:

    role_statement = (
        select(
            Role.id,
            Role.name,
        )
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user.id,
            Role.is_active.is_(True),
        )
        .order_by(Role.name)
    )

    roles = [
        {
            "id": row.id,
            "name": row.name,
        }
        for row in database.execute(
            role_statement
        ).all()
    ]

    scope_statement = (
        select(UserDataScope)
        .where(
            UserDataScope.user_id == user.id
        )
        .order_by(
            UserDataScope.scope_type,
            UserDataScope.scope_value,
        )
    )

    scopes = [
        {
            "id": scope.id,
            "scope_type": scope.scope_type,
            "scope_value": scope.scope_value,
            "is_active": scope.is_active,
        }
        for scope in database.scalars(
            scope_statement
        ).all()
    ]

    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "roles": roles,
        "scopes": scopes,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        ),
    }


# ============================================================
# LIST USERS
# ============================================================


@router.get("")
def list_users(
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.users.manage"
        )
    ),
):
    statement = (
        select(User)
        .order_by(
            User.full_name,
            User.username,
        )
    )

    users = list(
        database.scalars(
            statement
        ).all()
    )

    return {
        "data": [
            serialize_user(
                database,
                user,
            )
            for user in users
        ],
        "count": len(users),
    }


# ============================================================
# GET ONE USER
# ============================================================


@router.get("/{user_id}")
def get_admin_user(
    user_id: int,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.users.manage"
        )
    ),
):
    user = database.get(
        User,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "data": serialize_user(
            database,
            user,
        )
    }


# ============================================================
# CREATE USER
# ============================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_admin_user(
    payload: AdminUserCreate,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.users.manage"
        )
    ),
):
    existing_user = database.scalar(
        select(User)
        .where(
            or_(
                User.username
                == payload.username,

                User.email
                == str(payload.email),
            )
        )
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Username or email "
                "already exists"
            ),
        )

    role = database.scalar(
        select(Role)
        .where(
            Role.id == payload.role_id,
            Role.is_active.is_(True),
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Selected role does not exist "
                "or is inactive"
            ),
        )

    # ----------------------------------------------
    # Validate data scopes before creating anything
    # ----------------------------------------------

    for scope in payload.scopes:

        if (
            scope.scope_type
            == "enterprise"
        ):
            if scope.scope_value not in {
                None,
                "",
            }:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Enterprise scope must "
                        "not contain a scope value"
                    ),
                )

        elif scope.scope_type in {
            "department",
            "branch",
        }:
            if not (
                scope.scope_value
                and scope.scope_value.strip()
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{scope.scope_type.title()} "
                        "scope requires a value"
                    ),
                )

    # ----------------------------------------------
    # Create user
    # ----------------------------------------------

    user = User(
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        email=str(
            payload.email
        ).lower(),
        hashed_password=hash_password(
            payload.password
        ),

        # Legacy field only.
        # Authorization uses UserRole.
        role="user",

        is_active=True,
    )

    database.add(user)
    database.flush()

    # ----------------------------------------------
    # Assign RBAC role
    # ----------------------------------------------

    database.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
        )
    )

    # ----------------------------------------------
    # Assign data scopes
    # ----------------------------------------------

    for scope in payload.scopes:

        scope_value = (
            scope.scope_value.strip()
            if scope.scope_value
            else None
        )

        database.add(
            UserDataScope(
                user_id=user.id,
                scope_type=scope.scope_type,
                scope_value=scope_value,
                is_active=True,
            )
        )

    database.commit()
    database.refresh(user)

    return {
        "message": (
            "User created successfully"
        ),
        "data": serialize_user(
            database,
            user,
        ),
    }
