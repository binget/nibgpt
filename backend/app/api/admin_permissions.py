from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.rbac import Permission
from app.models.user import User
from app.services.rbac_service import require_permission


router = APIRouter(
    prefix="/api/admin/permissions",
    tags=["NIBGPT Administration - Permissions"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class AdminPermissionCreate(BaseModel):
    code: str = Field(
        min_length=3,
        max_length=150,
    )

    description: str | None = None


class AdminPermissionUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    description: str | None = None

    is_active: bool | None = None


# ============================================================
# SERIALIZER
# ============================================================


def serialize_permission(
    permission: Permission,
) -> dict:

    return {
        "id": permission.id,
        "code": permission.code,
        "description": permission.description,
        "is_active": permission.is_active,
        "created_at": (
            permission.created_at.isoformat()
            if permission.created_at
            else None
        ),
    }


# ============================================================
# LIST PERMISSIONS
# ============================================================


@router.get("")
def list_permissions(
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.permissions.manage"
        )
    ),
):
    permissions = list(
        database.scalars(
            select(Permission)
            .order_by(Permission.code)
        ).all()
    )

    return {
        "data": [
            serialize_permission(permission)
            for permission in permissions
        ],
        "count": len(permissions),
    }


# ============================================================
# GET PERMISSION
# ============================================================


@router.get("/{permission_id}")
def get_permission(
    permission_id: int,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.permissions.manage"
        )
    ),
):
    permission = database.get(
        Permission,
        permission_id,
    )

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    return {
        "data": serialize_permission(
            permission
        )
    }


# ============================================================
# CREATE PERMISSION
# ============================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_permission(
    payload: AdminPermissionCreate,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.permissions.manage"
        )
    ),
):
    permission_code = (
        payload.code.strip().lower()
    )

    existing_permission = database.scalar(
        select(Permission)
        .where(
            Permission.code
            == permission_code
        )
    )

    if existing_permission is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission already exists",
        )

    permission = Permission(
        code=permission_code,
        description=(
            payload.description.strip()
            if payload.description
            else None
        ),
        is_active=True,
    )

    database.add(permission)
    database.commit()
    database.refresh(permission)

    return {
        "message": (
            "Permission created successfully"
        ),
        "data": serialize_permission(
            permission
        ),
    }


# ============================================================
# UPDATE PERMISSION
# ============================================================


@router.put("/{permission_id}")
def update_permission(
    permission_id: int,
    payload: AdminPermissionUpdate,
    database: Session = Depends(get_db),
    _: User = Depends(
        require_permission(
            "admin.permissions.manage"
        )
    ),
):
    permission = database.get(
        Permission,
        permission_id,
    )

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    if payload.code is not None:

        permission_code = (
            payload.code.strip().lower()
        )

        duplicate = database.scalar(
            select(Permission)
            .where(
                Permission.code
                == permission_code,
                Permission.id
                != permission.id,
            )
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Permission already exists",
            )

        permission.code = (
            permission_code
        )

    if payload.description is not None:
        permission.description = (
            payload.description.strip()
            if payload.description
            else None
        )

    if payload.is_active is not None:

        # Protect the permission required to
        # administer permissions themselves.
        if (
            permission.code
            == "admin.permissions.manage"
            and not payload.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "The permission-management "
                    "permission cannot be disabled"
                ),
            )

        permission.is_active = (
            payload.is_active
        )

    database.commit()
    database.refresh(permission)

    return {
        "message": (
            "Permission updated successfully"
        ),
        "data": serialize_permission(
            permission
        ),
    }
