from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.query_planner import (
    CandidatePlan,
    create_query_plans,
)
from app.models.metadata import MetadataTable


ROLE_ROW_LIMITS = {
    "administrator": 1000,
    "data_steward": 500,
    "manager": 300,
    "analyst": 500,
    "standard_user": 100,
}


ROLE_ALLOWED_CLASSIFICATIONS = {
    "administrator": {
        "public",
        "internal",
        "confidential",
        "restricted",
    },
    "data_steward": {
        "public",
        "internal",
        "confidential",
        "restricted",
    },
    "manager": {
        "public",
        "internal",
        "confidential",
    },
    "analyst": {
        "public",
        "internal",
        "confidential",
    },
    "standard_user": {
        "public",
        "internal",
    },
}


SENSITIVE_COLUMN_ROLES = {
    "administrator",
    "data_steward",
    "analyst",
}


@dataclass
class RuleResult:
    rule_code: str
    rule_name: str
    passed: bool
    severity: str
    message: str


@dataclass
class GovernanceDecision:
    decision: str
    is_allowed: bool

    selected_plan_position: int | None = None
    selected_plan: CandidatePlan | None = None

    original_row_limit: int | None = None
    approved_row_limit: int | None = None

    requires_human_review: bool = False
    requires_user_selection: bool = False

    rule_results: list[RuleResult] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    blocked_reasons: list[str] = field(
        default_factory=list
    )


def add_rule(
    decision: GovernanceDecision,
    rule_code: str,
    rule_name: str,
    passed: bool,
    severity: str,
    message: str,
) -> None:
    decision.rule_results.append(
        RuleResult(
            rule_code=rule_code,
            rule_name=rule_name,
            passed=passed,
            severity=severity,
            message=message,
        )
    )

    if not passed:
        if severity == "critical":
            decision.blocked_reasons.append(
                message
            )
        else:
            decision.warnings.append(
                message
            )


def select_candidate_plan(
    candidate_plans: list[CandidatePlan],
    requested_position: int | None,
) -> CandidatePlan | None:
    if not candidate_plans:
        return None

    if requested_position is None:
        return candidate_plans[0]

    for plan in candidate_plans:
        if plan.position == requested_position:
            return plan

    return None


def load_table(
    database: Session,
    metadata_table_id: int,
) -> MetadataTable | None:
    statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
        )
        .where(
            MetadataTable.id
            == metadata_table_id
        )
    )

    return database.scalar(statement)


def evaluate_governance(
    database: Session,
    prompt: str,
    data_source_id: int | None,
    user_role: str,
    requested_plan_position: int | None,
    maximum_plans: int,
    requested_limit: int,
) -> GovernanceDecision:
    planning_result = create_query_plans(
        database=database,
        prompt=prompt,
        data_source_id=data_source_id,
        maximum_plans=maximum_plans,
        default_limit=requested_limit,
    )

    decision = GovernanceDecision(
        decision="blocked",
        is_allowed=False,
        requires_user_selection=planning_result[
            "requires_user_selection"
        ],
    )

    # Rule 1: Prompt must be read-only.
    is_safe = planning_result["is_safe"]

    add_rule(
        decision=decision,
        rule_code="READ_ONLY_001",
        rule_name="Read-only request",
        passed=is_safe,
        severity="critical",
        message=(
            "The request is read-only."
            if is_safe
            else (
                planning_result[
                    "blocked_reason"
                ]
                or "The request contains a prohibited write operation."
            )
        ),
    )

    if not is_safe:
        return decision

    candidate_plans = planning_result[
        "candidate_plans"
    ]

    selected_plan = select_candidate_plan(
        candidate_plans=candidate_plans,
        requested_position=requested_plan_position,
    )

    # Rule 2: A valid plan must exist.
    plan_exists = selected_plan is not None

    add_rule(
        decision=decision,
        rule_code="PLAN_001",
        rule_name="Valid query plan",
        passed=plan_exists,
        severity="critical",
        message=(
            "A valid query plan was selected."
            if plan_exists
            else "No valid query plan could be selected."
        ),
    )

    if selected_plan is None:
        return decision

    decision.selected_plan = selected_plan
    decision.selected_plan_position = (
        selected_plan.position
    )

    table = load_table(
        database=database,
        metadata_table_id=(
            selected_plan
            .table_match
            .table
            .id
        ),
    )

    table_exists = table is not None

    add_rule(
        decision=decision,
        rule_code="META_001",
        rule_name="Metadata object exists",
        passed=table_exists,
        severity="critical",
        message=(
            "The selected metadata table exists."
            if table_exists
            else "The selected metadata table no longer exists."
        ),
    )

    if table is None:
        return decision

    # Rule 3: Table must still exist in source.
    add_rule(
        decision=decision,
        rule_code="DISCOVERY_001",
        rule_name="Table is currently discovered",
        passed=table.is_discovered,
        severity="critical",
        message=(
            "The table currently exists in the connected data source."
            if table.is_discovered
            else "The table is no longer present in the connected data source."
        ),
    )

    # Rule 4: Catalogue object must be enabled.
    add_rule(
        decision=decision,
        rule_code="CATALOGUE_001",
        rule_name="Catalogue object enabled",
        passed=table.is_enabled,
        severity="critical",
        message=(
            "The table is enabled in the catalogue."
            if table.is_enabled
            else "The table is disabled in the catalogue."
        ),
    )

    # Rule 5: AI access must be enabled.
    add_rule(
        decision=decision,
        rule_code="AI_ACCESS_001",
        rule_name="AI access permitted",
        passed=table.ai_access_allowed,
        severity="critical",
        message=(
            "AI access is permitted for this table."
            if table.ai_access_allowed
            else "AI access is blocked for this table."
        ),
    )

    # Rule 6: Business definition approval.
    definition_approved = (
        table.definition_status == "approved"
    )

    add_rule(
        decision=decision,
        rule_code="DICTIONARY_001",
        rule_name="Business definition approved",
        passed=definition_approved,
        severity="warning",
        message=(
            "The Business Dictionary definition is approved."
            if definition_approved
            else (
                "The Business Dictionary definition "
                "has not been approved."
            )
        ),
    )

    if not definition_approved:
        decision.requires_human_review = True

    # Rule 7: Classification access.
    allowed_classifications = (
        ROLE_ALLOWED_CLASSIFICATIONS.get(
            user_role,
            {"public", "internal"},
        )
    )

    classification_allowed = (
        table.classification
        in allowed_classifications
    )

    add_rule(
        decision=decision,
        rule_code="CLASSIFICATION_001",
        rule_name="Classification access",
        passed=classification_allowed,
        severity="critical",
        message=(
            (
                f"Role '{user_role}' may access "
                f"'{table.classification}' data."
            )
            if classification_allowed
            else (
                f"Role '{user_role}' may not access "
                f"'{table.classification}' data."
            )
        ),
    )

    # Rule 8: Sensitive selected columns.
    selected_column_ids = {
        item.column.id
        for item in selected_plan.selected_columns
    }

    selected_column_ids.update(
        item.column.id
        for item in selected_plan.group_by
    )

    selected_column_ids.update(
        item.column.id
        for item in selected_plan.filters
    )

    if (
        selected_plan.aggregation
        and selected_plan.aggregation.column
    ):
        selected_column_ids.add(
            selected_plan
            .aggregation
            .column
            .id
        )

    selected_metadata_columns = [
        column
        for column in table.columns
        if column.id in selected_column_ids
    ]

    sensitive_columns = [
        column
        for column in selected_metadata_columns
        if column.is_sensitive
    ]

    sensitive_allowed = (
        not sensitive_columns
        or user_role in SENSITIVE_COLUMN_ROLES
    )

    sensitive_names = ", ".join(
        column.business_name
        or column.column_name
        for column in sensitive_columns
    )

    add_rule(
        decision=decision,
        rule_code="SENSITIVE_001",
        rule_name="Sensitive column access",
        passed=sensitive_allowed,
        severity="critical",
        message=(
            "No restricted sensitive columns are selected."
            if not sensitive_columns
            else (
                (
                    f"Role '{user_role}' may access sensitive columns: "
                    f"{sensitive_names}."
                )
                if sensitive_allowed
                else (
                    f"Role '{user_role}' may not access sensitive columns: "
                    f"{sensitive_names}."
                )
            )
        ),
    )

    # Rule 9: Every selected column must allow AI access.
    blocked_ai_columns = [
        column
        for column in selected_metadata_columns
        if not column.ai_access_allowed
    ]

    column_ai_allowed = (
        len(blocked_ai_columns) == 0
    )

    blocked_ai_names = ", ".join(
        column.business_name
        or column.column_name
        for column in blocked_ai_columns
    )

    add_rule(
        decision=decision,
        rule_code="AI_COLUMN_001",
        rule_name="Column AI permissions",
        passed=column_ai_allowed,
        severity="critical",
        message=(
            "All selected columns permit AI access."
            if column_ai_allowed
            else (
                "AI access is blocked for: "
                f"{blocked_ai_names}."
            )
        ),
    )

    # Rule 10: Confidence threshold.
    high_enough_confidence = (
        selected_plan.confidence >= 75
    )

    add_rule(
        decision=decision,
        rule_code="CONFIDENCE_001",
        rule_name="Minimum confidence",
        passed=high_enough_confidence,
        severity="warning",
        message=(
            (
                f"Plan confidence is sufficient "
                f"({selected_plan.confidence}%)."
            )
            if high_enough_confidence
            else (
                f"Plan confidence is only "
                f"{selected_plan.confidence}%."
            )
        ),
    )

    if not high_enough_confidence:
        decision.requires_human_review = True

    # Rule 11: Multiple close plans.
    if planning_result[
        "requires_user_selection"
    ]:
        add_rule(
            decision=decision,
            rule_code="PLAN_SELECTION_001",
            rule_name="Candidate plan ambiguity",
            passed=False,
            severity="warning",
            message=(
                "Multiple or low-confidence plans "
                "require user confirmation."
            ),
        )

        decision.requires_human_review = True
    else:
        add_rule(
            decision=decision,
            rule_code="PLAN_SELECTION_001",
            rule_name="Candidate plan ambiguity",
            passed=True,
            severity="info",
            message=(
                "The recommended plan is sufficiently distinct."
            ),
        )

    # Rule 12: Role-based row limit.
    role_limit = ROLE_ROW_LIMITS.get(
        user_role,
        100,
    )

    decision.original_row_limit = (
        selected_plan.row_limit
    )

    decision.approved_row_limit = min(
        selected_plan.row_limit,
        role_limit,
    )

    row_limit_unchanged = (
        selected_plan.row_limit
        <= role_limit
    )

    add_rule(
        decision=decision,
        rule_code="ROW_LIMIT_001",
        rule_name="Maximum result rows",
        passed=row_limit_unchanged,
        severity="warning",
        message=(
            (
                f"Requested row limit "
                f"{selected_plan.row_limit} is allowed."
            )
            if row_limit_unchanged
            else (
                f"Requested row limit "
                f"{selected_plan.row_limit} was reduced "
                f"to {role_limit} for role '{user_role}'."
            )
        ),
    )

    selected_plan.row_limit = (
        decision.approved_row_limit
    )

    critical_failures = [
        rule
        for rule in decision.rule_results
        if (
            not rule.passed
            and rule.severity == "critical"
        )
    ]

    if critical_failures:
        decision.decision = "blocked"
        decision.is_allowed = False
        return decision

    if decision.requires_human_review:
        decision.decision = (
            "requires_review"
        )
        decision.is_allowed = False
        return decision

    decision.decision = "approved"
    decision.is_allowed = True

    return decision
