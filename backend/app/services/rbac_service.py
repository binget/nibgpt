from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.database.session import get_db
from app.models.rbac import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    UserDataScope,
    UserRole,
)
from app.models.user import User


def get_user_permissions(
    database: Session,
    user_id: int,
) -> set[str]:
    statement = (
        select(Permission.code)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .join(
            Role,
            Role.id == RolePermission.role_id,
        )
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id,
            Role.is_active.is_(True),
            Permission.is_active.is_(True),
        )
    )

    return set(
        database.scalars(statement).all()
    )


def user_has_permission(
    database: Session,
    user_id: int,
    permission_code: str,
) -> bool:
    statement = (
        select(Permission.id)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .join(
            Role,
            Role.id == RolePermission.role_id,
        )
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id,
            Permission.code == permission_code,
            Role.is_active.is_(True),
            Permission.is_active.is_(True),
        )
        .limit(1)
    )

    return database.scalar(statement) is not None


def get_user_data_scopes(
    database: Session,
    user_id: int,
) -> list[UserDataScope]:
    statement = (
        select(UserDataScope)
        .where(
            UserDataScope.user_id == user_id,
            UserDataScope.is_active.is_(True),
        )
        .order_by(
            UserDataScope.scope_type,
            UserDataScope.scope_value,
        )
    )

    return list(
        database.scalars(statement).all()
    )


def log_access(
    database: Session,
    *,
    user_id: int | None,
    action: str,
    resource: str | None,
    permission_code: str | None,
    access_granted: bool,
    reason: str | None = None,
    request_text: str | None = None,
) -> AuditLog:
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        permission_code=permission_code,
        access_granted=access_granted,
        reason=reason,
        request_text=request_text,
    )

    database.add(audit)
    database.commit()
    database.refresh(audit)

    return audit


def require_permission(
    permission_code: str,
):
    def permission_dependency(
        current_user: User = Depends(get_current_user),
        database: Session = Depends(get_db),
    ) -> User:
        allowed = user_has_permission(
            database=database,
            user_id=current_user.id,
            permission_code=permission_code,
        )

        if not allowed:
            log_access(
                database,
                user_id=current_user.id,
                action="permission_check",
                resource=None,
                permission_code=permission_code,
                access_granted=False,
                reason="Required permission not assigned",
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. "
                    f"Missing permission: {permission_code}"
                ),
            )

        log_access(
            database,
            user_id=current_user.id,
            action="permission_check",
            resource=None,
            permission_code=permission_code,
            access_granted=True,
            reason="Permission granted",
        )

        return current_user

    return permission_dependency

def authorize_request(
    database: Session,
    *,
    user: User,
    permission_code: str,
    resource: str,
    request_text: str | None = None,
) -> None:

    allowed = user_has_permission(
        database=database,
        user_id=user.id,
        permission_code=permission_code,
    )

    if not allowed:
        log_access(
            database,
            user_id=user.id,
            action="orchestrator_authorization",
            resource=resource,
            permission_code=permission_code,
            access_granted=False,
            reason="Required permission not assigned",
            request_text=request_text,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied. "
                f"Missing permission: {permission_code}"
            ),
        )

    log_access(
        database,
        user_id=user.id,
        action="orchestrator_authorization",
        resource=resource,
        permission_code=permission_code,
        access_granted=True,
        reason="Permission granted",
        request_text=request_text,
    )
    
def get_user_governance_role(
    database: Session,
    user_id: int,
) -> str:
    statement = (
        select(Role.name)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id,
            Role.is_active.is_(True),
        )
        .order_by(Role.id)
    )

    role_names = set(
        database.scalars(statement).all()
    )

    # RBAC role -> legacy governance profile.
    #
    # This mapping is server-controlled.
    # The browser must never choose its own
    # governance profile.

    if "admin" in role_names:
        return "administrator"

    if "data_steward" in role_names:
        return "data_steward"

    if "manager" in role_names:
        return "manager"

    if "analyst" in role_names:
        return "analyst"

    return "standard_user"