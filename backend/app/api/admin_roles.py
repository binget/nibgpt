from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
)
from app.models.user import User
from app.services.rbac_service import require_permission


router = APIRouter(
    prefix="/api/admin/roles",
    tags=["NIBGPT Administration - Roles"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class AdminRoleCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    description: str | None = None

    permission_ids: list[int] = []


class AdminRoleUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    description: str | None = None

    is_active: bool | None = None

    permission_ids: list[int] | None = None


# ============================================================
# SERIALIZER
# ============================================================


def serialize_role(
    database: Session,
    role: Role,
) -> dict:

    permission_statement = (
        select(
            Permission.id,
            Permission.code,
            Permission.description,
            Permission.is_active,
        )
        .join(
            RolePermission,
            RolePermission.permission_id
            == Permission.id,
        )
        .where(
            RolePermission.role_id
            == role.id
        )
        .order_by(
            Permission.code
        )
    )

    permissions = [
        {
            "id": row.id,
            "code": row.code,
            "description": row.description,
            "is_active": row.is_active,
        }
        for row in database.execute(
            permission_statement
        ).all()
    ]

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "permissions": permissions,
        "created_at": (
            role.created_at.isoformat()
            if role.created_at
            else None
        ),
    }


# ============================================================
# PERMISSION VALIDATION
# ============================================================


def validate_permission_ids(
    database: Session,
    permission_ids: list[int],
) -> list[Permission]:

    if not permission_ids:
        return []

    unique_ids = list(
        dict.fromkeys(permission_ids)
    )

    statement = (
        select(Permission)
        .where(
            Permission.id.in_(unique_ids),
            Permission.is_active.is_(True),
        )
    )

    permissions = list(
        database.scalars(
            statement
        ).all()
    )

    found_ids = {
        permission.id
        for permission in permissions
    }

    missing_ids = [
        permission_id
        for permission_id in unique_ids
        if permission_id not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "One or more permissions "
                    "do not exist or are inactive"
                ),
                "permission_ids": missing_ids,
            },
        )

    return permissions


# ============================================================
# LIST ROLES
# ============================================================


@router.get("")
def list_roles(
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.roles.manage"
        )
    ),
):
    roles = list(
        database.scalars(
            select(Role)
            .order_by(Role.name)
        ).all()
    )

    return {
        "data": [
            serialize_role(
                database,
                role,
            )
            for role in roles
        ],
        "count": len(roles),
    }


# ============================================================
# GET ROLE
# ============================================================


@router.get("/{role_id}")
def get_role(
    role_id: int,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.roles.manage"
        )
    ),
):
    role = database.get(
        Role,
        role_id,
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return {
        "data": serialize_role(
            database,
            role,
        )
    }


# ============================================================
# CREATE ROLE
# ============================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    payload: AdminRoleCreate,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.roles.manage"
        )
    ),
):
    role_name = (
        payload.name.strip()
    )

    existing_role = database.scalar(
        select(Role)
        .where(
            Role.name == role_name
        )
    )

    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role already exists",
        )

    permissions = validate_permission_ids(
        database,
        payload.permission_ids,
    )

    role = Role(
        name=role_name,
        description=(
            payload.description.strip()
            if payload.description
            else None
        ),
        is_active=True,
    )

    database.add(role)
    database.flush()

    for permission in permissions:
        database.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )
        )

    database.commit()
    database.refresh(role)

    return {
        "message": (
            "Role created successfully"
        ),
        "data": serialize_role(
            database,
            role,
        ),
    }


# ============================================================
# UPDATE ROLE
# ============================================================


@router.put("/{role_id}")
def update_role(
    role_id: int,
    payload: AdminRoleUpdate,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.roles.manage"
        )
    ),
):
    role = database.get(
        Role,
        role_id,
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if payload.name is not None:

        role_name = (
            payload.name.strip()
        )

        duplicate = database.scalar(
            select(Role)
            .where(
                Role.name == role_name,
                Role.id != role.id,
            )
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role already exists",
            )

        role.name = role_name

    if payload.description is not None:
        role.description = (
            payload.description.strip()
            if payload.description
            else None
        )

    if payload.is_active is not None:

        if (
            role.name == "admin"
            and not payload.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "The admin role cannot "
                    "be disabled"
                ),
            )

        role.is_active = (
            payload.is_active
        )

    if payload.permission_ids is not None:

        permissions = validate_permission_ids(
            database,
            payload.permission_ids,
        )

        database.execute(
            delete(RolePermission)
            .where(
                RolePermission.role_id
                == role.id
            )
        )

        for permission in permissions:
            database.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )

    database.commit()
    database.refresh(role)

    return {
        "message": (
            "Role updated successfully"
        ),
        "data": serialize_role(
            database,
            role,
        ),
    }
