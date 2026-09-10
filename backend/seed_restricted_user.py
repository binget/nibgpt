from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    UserDataScope,
    UserRole,
)
from app.models.user import User


def main():
    database = SessionLocal()

    try:
        # -------------------------------------------------
        # ROLE
        # -------------------------------------------------
        role = database.scalar(
            select(Role).where(
                Role.name == "standard_user"
            )
        )

        if role is None:
            role = Role(
                name="standard_user",
                description="Standard NIBGPT user with restricted access",
                is_active=True,
            )

            database.add(role)
            database.flush()

        # -------------------------------------------------
        # SAFE BASE PERMISSIONS ONLY
        # -------------------------------------------------
        allowed_permissions = [
            "nibgpt.use",
            "documents.view",
            "reports.view",
            "competitor.view",
        ]

        for code in allowed_permissions:
            permission = database.scalar(
                select(Permission).where(
                    Permission.code == code
                )
            )

            if permission is None:
                raise RuntimeError(
                    f"Permission not found: {code}"
                )

            existing = database.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )

            if existing is None:
                database.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

        # -------------------------------------------------
        # TEST USER
        # -------------------------------------------------
        user = database.scalar(
            select(User).where(
                User.username == "user"
            )
        )

        if user is None:
            user = User(
                username="user",
                full_name="NIBGPT Test User",
                email="user@nibbank.com",
                hashed_password=hash_password(
                    "user"
                ),
                role="user",
                is_active=True,
            )

            database.add(user)
            database.flush()

        # -------------------------------------------------
        # USER ROLE
        # -------------------------------------------------
        existing_user_role = database.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )

        if existing_user_role is None:
            database.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                )
            )

        # -------------------------------------------------
        # BRANCH-LIMITED DATA SCOPE
        # -------------------------------------------------
        existing_scope = database.scalar(
            select(UserDataScope).where(
                UserDataScope.user_id == user.id,
                UserDataScope.scope_type == "branch",
                UserDataScope.scope_value == "001",
            )
        )

        if existing_scope is None:
            database.add(
                UserDataScope(
                    user_id=user.id,
                    scope_type="branch",
                    scope_value="001",
                    is_active=True,
                )
            )

        database.commit()

        print("Restricted test user created.")
        print("Username: user")
        print("Password: user")
        print("Role: standard_user")
        print("Scope: branch:001")
        print(
            "Account balance permission: NOT ASSIGNED"
        )

    except Exception:
        database.rollback()
        raise

    finally:
        database.close()


if __name__ == "__main__":
    main()
