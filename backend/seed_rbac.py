from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    UserDataScope,
    UserRole,
)
from app.models.user import User


PERMISSIONS = {
    "nibgpt.use":
        "Use the NIBGPT platform",

    "documents.view":
        "View approved documents",

    "documents.confidential.view":
        "View confidential approved documents",

    "reports.view":
        "View normal reports",

    "reports.enterprise.view":
        "View enterprise-wide reports",

    "customer.profile.view":
        "View customer profile information",

    "account.balance.view":
        "View customer account balances",

    "account.transactions.view":
        "View customer account transactions",

    "deposit.summary.view":
        "View deposit summaries",

    "deposit.forecast.view":
        "View deposit forecasts",

    "account_opening.analytics.view":
        "View account opening analytics",

    "account_opening.forecast.view":
        "View account opening forecasts",

    "competitor.view":
        "View competitor intelligence",

    "admin.users.manage":
        "Manage NIBGPT users",

    "admin.roles.manage":
        "Manage NIBGPT roles",

    "admin.permissions.manage":
        "Manage NIBGPT permissions",
}


def get_or_create_role(
    database,
    name: str,
    description: str,
):
    role = database.scalar(
        select(Role).where(
            Role.name == name
        )
    )

    if role:
        return role

    role = Role(
        name=name,
        description=description,
        is_active=True,
    )

    database.add(role)
    database.flush()

    return role


def get_or_create_permission(
    database,
    code: str,
    description: str,
):
    permission = database.scalar(
        select(Permission).where(
            Permission.code == code
        )
    )

    if permission:
        return permission

    permission = Permission(
        code=code,
        description=description,
        is_active=True,
    )

    database.add(permission)
    database.flush()

    return permission


def main():
    database = SessionLocal()

    try:
        admin_role = get_or_create_role(
            database,
            name="admin",
            description="NIBGPT platform administrator",
        )

        permissions = []

        for code, description in PERMISSIONS.items():
            permission = get_or_create_permission(
                database,
                code=code,
                description=description,
            )

            permissions.append(permission)

        database.flush()

        for permission in permissions:
            existing = database.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == permission.id,
                )
            )

            if existing is None:
                database.add(
                    RolePermission(
                        role_id=admin_role.id,
                        permission_id=permission.id,
                    )
                )

        admin_user = database.scalar(
            select(User).where(
                User.username == "admin"
            )
        )

        if admin_user is None:
            raise RuntimeError(
                "Admin user was not found."
            )

        existing_user_role = database.scalar(
            select(UserRole).where(
                UserRole.user_id == admin_user.id,
                UserRole.role_id == admin_role.id,
            )
        )

        if existing_user_role is None:
            database.add(
                UserRole(
                    user_id=admin_user.id,
                    role_id=admin_role.id,
                )
            )

        existing_scope = database.scalar(
            select(UserDataScope).where(
                UserDataScope.user_id == admin_user.id,
                UserDataScope.scope_type == "enterprise",
                UserDataScope.scope_value == "*",
            )
        )

        if existing_scope is None:
            database.add(
                UserDataScope(
                    user_id=admin_user.id,
                    scope_type="enterprise",
                    scope_value="*",
                    is_active=True,
                )
            )

        database.commit()

        print("NIBGPT RBAC seed completed.")
        print(
            f"Admin user: {admin_user.username}"
        )
        print(
            f"Role: {admin_role.name}"
        )
        print(
            f"Permissions: {len(permissions)}"
        )
        print(
            "Scope: enterprise:*"
        )

    except Exception:
        database.rollback()
        raise

    finally:
        database.close()


if __name__ == "__main__":
    main()
