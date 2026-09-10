from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationRequirement:
    permission_code: str
    resource: str


def resolve_authorization_requirement(
    prompt: str,
    route: str,
) -> AuthorizationRequirement:

    normalized = " ".join(
        (prompt or "")
        .lower()
        .strip()
        .split()
    )

    # ---------------------------------------------------------
    # Sensitive account-level access
    # ---------------------------------------------------------

    if (
        "balance" in normalized
        and (
            "account" in normalized
            or "customer" in normalized
        )
    ):
        return AuthorizationRequirement(
            permission_code="account.balance.view",
            resource="account_balance",
        )

    if (
        "transaction" in normalized
        or "transactions" in normalized
        or "statement" in normalized
    ):
        return AuthorizationRequirement(
            permission_code="account.transactions.view",
            resource="account_transactions",
        )

    # ---------------------------------------------------------
    # Forecasting
    # ---------------------------------------------------------

    if (
        "forecast" in normalized
        and "deposit" in normalized
    ):
        return AuthorizationRequirement(
            permission_code="deposit.forecast.view",
            resource="deposit_forecast",
        )

    if (
        "forecast" in normalized
        and (
            "account opening" in normalized
            or "account openings" in normalized
        )
    ):
        return AuthorizationRequirement(
            permission_code="account_opening.forecast.view",
            resource="account_opening_forecast",
        )

    # ---------------------------------------------------------
    # Analytics
    # ---------------------------------------------------------

    if (
        "account opening" in normalized
        or "account openings" in normalized
    ):
        return AuthorizationRequirement(
            permission_code="account_opening.analytics.view",
            resource="account_opening_analytics",
        )

    if (
        route == "reporting"
        and "deposit" in normalized
    ):
        return AuthorizationRequirement(
            permission_code="deposit.summary.view",
            resource="deposit_summary",
        )

    # ---------------------------------------------------------
    # Documents
    # ---------------------------------------------------------

    if route in {
        "knowledge",
        "document",
    }:
        return AuthorizationRequirement(
            permission_code="documents.view",
            resource="documents",
        )

    # ---------------------------------------------------------
    # Competitor intelligence
    # ---------------------------------------------------------

    if route == "competitor":
        return AuthorizationRequirement(
            permission_code="competitor.view",
            resource="competitor_intelligence",
        )

    # ---------------------------------------------------------
    # General reporting
    # ---------------------------------------------------------

    if route == "reporting":
        return AuthorizationRequirement(
            permission_code="reports.view",
            resource="reporting",
        )

    # ---------------------------------------------------------
    # General NIBGPT usage
    # ---------------------------------------------------------

    return AuthorizationRequirement(
        permission_code="nibgpt.use",
        resource="nibgpt",
    )