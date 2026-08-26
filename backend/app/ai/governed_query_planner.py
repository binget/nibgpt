import re
from dataclasses import dataclass, field
from typing import Any

from click import prompt

from sqlalchemy.orm import Session

from app.ai.entity_extractor import (
    extract_entities,
)
from app.ai.relationship_reasoning import (
    ResolvedColumn,
    analyze_relationship_reasoning,
)

from app.models.business_rule import (
    BusinessRule,
)

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.business_join_mapping import (
    BusinessRelationshipJoinMapping,
)

from app.models.business_rule import (
    BusinessRule,
)

from app.models.business_measure import (
    BusinessMeasure,
)

from app.models.business_dimension import (
    BusinessDimension,
)


ROLE_ROW_LIMITS = {
    "administrator": 1000,
    "data_steward": 500,
    "knowledge_steward": 500,
    "analyst": 500,
    "manager": 300,
    "executive": 300,
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
    "knowledge_steward": {
        "public",
        "internal",
        "confidential",
        "restricted",
    },
    "analyst": {
        "public",
        "internal",
        "confidential",
    },
    "manager": {
        "public",
        "internal",
        "confidential",
    },
    "executive": {
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


NUMERIC_TYPES = {
    "int",
    "integer",
    "bigint",
    "smallint",
    "decimal",
    "numeric",
    "number",
    "float",
    "double",
    "real",
    "money",
}


DATE_TYPES = {
    "date",
    "datetime",
    "timestamp",
    "time",
}


MEASURE_TERMS = {
    "amount",
    "balance",
    "quantity",
    "price",
    "total",
    "cost",
    "value",
    "rate",
    "revenue",
    "expense",
    "payment",
    "deposit",
}


DISPLAY_TERMS = {
    "name",
    "number",
    "code",
    "reference",
    "status",
    "date",
    "branch",
    "department",
    "type",
    "category",
}


@dataclass
class GovernanceCheck:
    rule_code: str
    passed: bool
    severity: str
    message: str


@dataclass
class PlannedColumn:
    table: object
    resolved_column: object
    purpose: str
    confidence: int


@dataclass
class PlannedFilter:
    table: object
    resolved_column: object
    operator: str
    value: Any
    confidence: int
    reason: str


@dataclass
class PlannedAggregation:
    function: str
    table: object | None
    resolved_column: object | None
    alias: str
    confidence: int


@dataclass
class PlannedGrouping:
    table: object
    resolved_column: object
    confidence: int


@dataclass
class PlannedSort:
    table: object
    resolved_column: object
    direction: str
    confidence: int


@dataclass
class GovernedPlan:
    decision: str
    is_allowed: bool

    prompt: str
    normalized_prompt: str
    intent: str

    reasoning_result: dict

    selected_columns: list[
        PlannedColumn
    ] = field(default_factory=list)

    filters: list[
        PlannedFilter
    ] = field(default_factory=list)

    # Existing single aggregation.
    # Keep this for backward compatibility.
    aggregation: (
        PlannedAggregation | None
    ) = None

    # New multi-measure support.
    aggregations: list[
        PlannedAggregation
    ] = field(default_factory=list)

    group_by: list[
        PlannedGrouping
    ] = field(default_factory=list)

    order_by: list[
        PlannedSort
    ] = field(default_factory=list)

    approved_limit: int = 100

    governance_checks: list[
        GovernanceCheck
    ] = field(default_factory=list)

    warnings: list[str] = field(
        default_factory=list
    )

    blocked_reasons: list[str] = field(
        default_factory=list
    )

    explanation: list[str] = field(
        default_factory=list
    )

    join_mappings: dict[
    int,
    BusinessRelationshipJoinMapping,
    ] = field(default_factory=dict)

    overall_confidence: int = 0


def normalize_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    normalized = value.lower()

    normalized = re.sub(
        r"[_\-]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"[^a-z0-9\s]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def is_numeric_type(
    data_type: str,
) -> bool:
    normalized = normalize_text(
        data_type
    )

    return any(
        term in normalized
        for term in NUMERIC_TYPES
    )


def is_date_type(
    data_type: str,
) -> bool:
    normalized = normalize_text(
        data_type
    )

    return any(
        term in normalized
        for term in DATE_TYPES
    )


def column_search_text(
    resolved_column: object,
) -> str:
    column = resolved_column.column

    return normalize_text(
        " ".join(
            filter(
                None,
                [
                    column.column_name,
                    column.business_name,
                    column.description,
                    " ".join(
                        resolved_column
                        .matched_terms
                    ),
                ],
            )
        )
    )


def add_governance_check(
    plan: GovernedPlan,
    rule_code: str,
    passed: bool,
    severity: str,
    message: str,
) -> None:
    plan.governance_checks.append(
        GovernanceCheck(
            rule_code=rule_code,
            passed=passed,
            severity=severity,
            message=message,
        )
    )

    if not passed:
        if severity == "critical":
            plan.blocked_reasons.append(
                message
            )
        else:
            plan.warnings.append(
                message
            )


def find_best_column(
    physical_tables: list[object],
    terms: list[str],
    require_numeric: bool = False,
    require_date: bool = False,
    exclude_primary_key: bool = False,
    preferred_entity_terms: list[str] | None = None,
) -> tuple[
    object,
    ResolvedColumn,
] | None:
    best_match = None
    best_score = 0

    normalized_terms = [
        normalize_text(term)
        for term in terms
        if normalize_text(term)
    ]

    normalized_entity_terms = [
        normalize_text(term)
        for term in (
            preferred_entity_terms
            or []
        )
        if normalize_text(term)
    ]

    for resolved_table in physical_tables:
        table = resolved_table.table

        entity_name = normalize_text(
            resolved_table.entity.name
        )

        for column in table.columns:
            if (
                not column.is_discovered
                or not column.is_enabled
                or not column.ai_access_allowed
            ):
                continue

            if (
                exclude_primary_key
                and column.is_primary_key
            ):
                continue

            if (
                require_numeric
                and not is_numeric_type(
                    column.data_type
                )
            ):
                continue

            if (
                require_date
                and not is_date_type(
                    column.data_type
                )
            ):
                continue

            column_name = normalize_text(
                column.column_name
            )

            business_name = normalize_text(
                column.business_name
            )

            description = normalize_text(
                column.description
            )

            score = 0
            matched_terms: list[str] = []

            for term in normalized_terms:
                if (
                    term == column_name
                    or term == business_name
                ):
                    score += 120
                    matched_terms.append(
                        term
                    )

                elif (
                    f" {term} "
                    in f" {column_name} "
                    or f" {term} "
                    in f" {business_name} "
                ):
                    score += 75
                    matched_terms.append(
                        term
                    )

                elif (
                    term in column_name
                    or term in business_name
                ):
                    score += 45
                    matched_terms.append(
                        term
                    )

                elif (
                    description
                    and term
                    in description
                ):
                    score += 15
                    matched_terms.append(
                        term
                    )

            # Prefer a column from the entity that
            # the local phrase refers to.
            for entity_term in (
                normalized_entity_terms
            ):
                if (
                    entity_term
                    and (
                        entity_term
                        in entity_name
                        or entity_name
                        in entity_term
                    )
                ):
                    score += 50

            # No semantic match means this column
            # must not become a candidate.
            if score <= 0:
                continue

            confidence = min(
                99,
                max(
                    55,
                    round(
                        score / 1.5
                    ),
                ),
            )

            if score > best_score:
                best_score = score

                best_match = (
                    resolved_table,
                    ResolvedColumn(
                        column=column,
                        confidence=confidence,
                        matched_terms=list(
                            dict.fromkeys(
                                matched_terms
                            )
                        ),
                    ),
                )

    return best_match


def choose_display_columns(
    physical_tables: list[object],
    maximum_columns: int = 10,
) -> list[PlannedColumn]:
    candidates: list[
        PlannedColumn
    ] = []

    used_column_ids: set[int] = set()

    for resolved_table in physical_tables:
        for resolved_column in (
            resolved_table.columns
        ):
            column = (
                resolved_column.column
            )

            if column.id in used_column_ids:
                continue

            searchable = (
                column_search_text(
                    resolved_column
                )
            )

            purpose = "result"

            if column.is_primary_key:
                purpose = "identifier"

            elif any(
                term in searchable
                for term in DISPLAY_TERMS
            ):
                purpose = "display"

            elif is_date_type(
                column.data_type
            ):
                purpose = "date"

            elif is_numeric_type(
                column.data_type
            ):
                purpose = "measure"

            candidates.append(
                PlannedColumn(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    purpose=purpose,
                    confidence=(
                        resolved_column
                        .confidence
                    ),
                )
            )

            used_column_ids.add(
                column.id
            )

    candidates.sort(
        key=lambda item: (
            item.purpose
            not in {
                "identifier",
                "display",
                "date",
            },
            -item.confidence,
        )
    )

    return candidates[
        :maximum_columns
    ]


def detect_requested_limit(
    prompt: str,
    requested_limit: int,
    role_limit: int,
) -> int:
    normalized = normalize_text(
        prompt
    )

    # --------------------------------------------------
    # Dynamic user-requested ranking limit
    #
    # Examples:
    # top 5
    # top 10
    # top 25
    # bottom 7
    # first 50
    # last 20
    # --------------------------------------------------

    match = re.search(
        r"\b(?:top|bottom|first|last)"
        r"\s+(\d+)\b",
        normalized,
    )

    if match:
        prompt_limit = int(
            match.group(1)
        )
    else:
        prompt_limit = (
            requested_limit
        )

    return min(
        max(
            prompt_limit,
            1,
        ),
        role_limit,
        1000,
    )


def determine_time_operator(
    time_expression: str,
) -> str | None:
    mapping = {
        "today": "this_day",
        "this week": "this_week",
        "this month": "this_month",
        "this year": "this_year",
        "yesterday": "last_day",
        "last week": "last_week",
        "last month": "last_month",
        "last year": "last_year",
        "tomorrow": "next_day",
        "next week": "next_week",
        "next month": "next_month",
        "next year": "next_year",
    }

    return mapping.get(
        normalize_text(
            time_expression
        )
    )


def build_time_filters(
    prompt: str,
    physical_tables: list[object],
    time_expressions: list[str],
) -> list[PlannedFilter]:
    filters: list[PlannedFilter] = []

    normalized_prompt = normalize_text(prompt)

    if "completed" in normalized_prompt:
        context_date_terms = [
            "date completed",
            "completed date",
            "completion date",
        ]
    elif "assigned" in normalized_prompt:
        context_date_terms = [
            "date assigned",
            "assigned date",
            "assignment date",
        ]
    elif (
        "rejected" in normalized_prompt
        or "reject" in normalized_prompt
    ):
        context_date_terms = [
            "date rejected",
            "rejected date",
            "rejection date",
        ]
    elif (
        "registered" in normalized_prompt
        or "registration" in normalized_prompt
    ):
        context_date_terms = [
            "date registered",
            "registered date",
            "registration date",
        ]
    elif (
        "expire" in normalized_prompt
        or "expired" in normalized_prompt
        or "expiry" in normalized_prompt
    ):
        context_date_terms = [
            "license expiry date",
            "insurance expiry date",
            "expiry date",
            "expiration date",
        ]
    else:
        context_date_terms = [
            "start date",
            "request date",
            "transaction date",
            "date registered",
            "created date",
            "date",
        ]

    for expression in time_expressions:
        operator = determine_time_operator(
            expression
        )

        if operator is None:
            continue

        match = find_best_column(
            physical_tables=physical_tables,
            terms=context_date_terms,
            require_date=True,
        )

        if match is None:
            continue

        (
            resolved_table,
            resolved_column,
        ) = match

        filters.append(
            PlannedFilter(
                table=resolved_table,
                resolved_column=resolved_column,
                operator=operator,
                value=None,
                confidence=92,
                reason=(
                    f"Time expression '{expression}' "
                    f"was mapped to contextual date column "
                    f"{resolved_column.column.column_name}."
                ),
            )
        )

    return filters

def build_status_filters(
    prompt: str,
    physical_tables: list[object],
    status_terms: list[str],
) -> list[PlannedFilter]:
    filters: list[
        PlannedFilter
    ] = []

    normalized_prompt = (
        normalize_text(prompt)
    )

    words = (
        normalized_prompt.split()
    )

    for status_term in status_terms:
        normalized_status = (
            normalize_text(
                status_term
            )
        )

        # --------------------------------------------------
        # Core Banking account activity
        #
        # Active / inactive account semantics are handled
        # by governed BusinessRule entries inside
        # build_attribute_filters().
        #
        # Do not create another INACTIVMARKER filter here.
        # --------------------------------------------------

        if normalized_status in {
            "active",
            "inactive",
        }:
            continue

        # --------------------------------------------------
        # Expiry language
        #
        # Expiry is handled by the expiry-date resolver,
        # not by generic status matching.
        # --------------------------------------------------

        if normalized_status in {
            "expired",
            "expire",
            "expires",
            "expiring",
        }:
            continue

        preferred_terms: list[str] = []

        try:
            position = words.index(
                normalized_status
            )

            start = max(
                0,
                position - 2,
            )

            end = min(
                len(words),
                position + 4,
            )

            preferred_terms = (
                words[start:end]
            )

        except ValueError:
            pass

        match = find_best_column(
            physical_tables=(
                physical_tables
            ),
            terms=[
                "status",
                "approval status",
                "state",
            ],
            preferred_entity_terms=(
                preferred_terms
            ),
        )

        if match is None:
            continue

        (
            resolved_table,
            resolved_column,
        ) = match

        filters.append(
            PlannedFilter(
                table=resolved_table,
                resolved_column=(
                    resolved_column
                ),
                operator="=",
                value=status_term,
                confidence=90,
                reason=(
                    f"Status '{status_term}' "
                    f"was mapped to "
                    f"{resolved_table.entity.name}."
                    f"{resolved_column.column.column_name}."
                ),
            )
        )

    return filters

def build_attribute_filters(
    database: Session,
    prompt: str,
    physical_tables: list[object],
) -> list[PlannedFilter]:
    filters: list[PlannedFilter] = []

    normalized_prompt = normalize_text(
        prompt
    )

    matched_rule_ids: set[int] = set()

    # --------------------------------------------------
    # Helper: whole-word / whole-phrase matching
    #
    # Prevents:
    #
    # "active" matching "inactive"
    #
    # Supports:
    #
    # deposit
    # deposit balance
    # active account
    # etc.
    # --------------------------------------------------

    def phrase_matches(
        phrase: str,
    ) -> bool:
        normalized_phrase = normalize_text(
            phrase
        )

        if not normalized_phrase:
            return False

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(
                normalized_phrase
            )
            + r"(?![a-z0-9])"
        )

        return (
            re.search(
                pattern,
                normalized_prompt,
            )
            is not None
        )

    # --------------------------------------------------
    # Determine whether the question is about accounts.
    #
    # Normal account analytics must use the governed
    # customer/deposit account scope.
    #
    # FBNK_ACCOUNT.CATEGORY:
    #
    # 1001 - 1099
    # 6501 - 6600
    # --------------------------------------------------

    account_scope_prompt = (
        phrase_matches(
            "account"
        )
        or phrase_matches(
            "accounts"
        )
        or phrase_matches(
            "account balance"
        )
        or phrase_matches(
            "account balances"
        )
        or phrase_matches(
            "deposit"
        )
        or phrase_matches(
            "deposits"
        )
        or phrase_matches(
            "deposit balance"
        )
        or phrase_matches(
            "deposit balances"
        )
        or phrase_matches(
            "number of accounts"
        )
        or phrase_matches(
            "number of account"
        )
        or phrase_matches(
            "how many accounts"
        )
        or phrase_matches(
            "how many account"
        )
        or phrase_matches(
            "account report"
        )
    )

    # --------------------------------------------------
    # Deposit BALANCE calculation.
    #
    # This is deliberately separate from account count.
    #
    # CATEGORY 1011 remains part of the deposit scope,
    # but for balance calculations we include CATEGORY
    # 1011 only when WORKINGBALANCE > 0.
    # --------------------------------------------------

    deposit_balance_prompt = (
        phrase_matches(
            "deposit balance"
        )
        or phrase_matches(
            "deposit balances"
        )
        or phrase_matches(
            "total deposit balance"
        )
        or (
            phrase_matches(
                "deposit"
            )
            and phrase_matches(
                "balance"
            )
        )
    )

    # --------------------------------------------------
    # 1. Load approved metadata-driven business rules
    # --------------------------------------------------

    statement = (
        select(
            BusinessRule
        )
        .where(
            BusinessRule.approval_status
            == "approved",
            BusinessRule.is_active.is_(
                True
            ),
        )
    )

    business_rules = list(
        database.scalars(
            statement
        ).all()
    )

    # --------------------------------------------------
    # 2. Apply approved business rules
    # --------------------------------------------------

    for rule in business_rules:
        if rule.id in matched_rule_ids:
            continue

        rule_name = normalize_text(
            rule.name
        )

        trigger = normalize_text(
            rule.trigger_phrase
        )

        synonyms: list[str] = []

        # --------------------------------------------------
        # Parse synonyms.
        #
        # Supports JSON:
        #
        # ["deposit account", "deposit accounts"]
        #
        # and comma separated values.
        # --------------------------------------------------

        if rule.synonyms:
            try:
                import json

                parsed = json.loads(
                    rule.synonyms
                )

                if isinstance(
                    parsed,
                    list,
                ):
                    synonyms = [
                        normalize_text(
                            str(item)
                        )
                        for item
                        in parsed
                        if str(
                            item
                        ).strip()
                    ]

            except Exception:
                synonyms = [
                    normalize_text(
                        item
                    )
                    for item
                    in rule.synonyms.split(
                        ","
                    )
                    if item.strip()
                ]

        # --------------------------------------------------
        # Active / inactive account status is handled
        # centrally by build_status_filters().
        #
        # Do not apply the BusinessRule copy again here,
        # otherwise:
        #
        # INACTIVMARKER = 'Y'
        #
        # could appear twice.
        # --------------------------------------------------

        if rule_name in {
            "active account",
            "inactive account",
        }:
            continue

        # --------------------------------------------------
        # Normal trigger matching
        # --------------------------------------------------

        trigger_matches = False

        if (
            trigger
            and phrase_matches(
                trigger
            )
        ):
            trigger_matches = True

        if not trigger_matches:
            for synonym in synonyms:
                if (
                    synonym
                    and phrase_matches(
                        synonym
                    )
                ):
                    trigger_matches = True
                    break

        # --------------------------------------------------
        # Force governed deposit-account scope for normal
        # account reporting.
        #
        # This allows prompts such as:
        #
        # Show number of active accounts
        # Show account balance
        # Show active account report by branch
        #
        # to inherit the Deposit Accounts CATEGORY rule
        # even when the user does not literally say
        # "deposit".
        # --------------------------------------------------

        force_account_scope = (
            account_scope_prompt
            and rule_name
            == "deposit accounts"
        )

        if (
            not trigger_matches
            and not force_account_scope
        ):
            continue

        # --------------------------------------------------
        # Find the physical entity/table already selected
        # by relationship reasoning.
        # --------------------------------------------------

        rule_applied = False

        for resolved_table in physical_tables:
            if (
                resolved_table.entity.id
                != rule.business_entity_id
            ):
                continue

            for column in (
                resolved_table.table.columns
            ):
                if (
                    column.id
                    != rule.metadata_column_id
                ):
                    continue

                if (
                    not column.is_discovered
                    or not column.is_enabled
                    or not column.ai_access_allowed
                ):
                    continue

                matched_term = (
                    trigger
                    if trigger
                    else rule.name
                )

                resolved_column = (
                    ResolvedColumn(
                        column=column,
                        confidence=(
                            rule.confidence
                        ),
                        matched_terms=[
                            matched_term
                        ],
                    )
                )

                filters.append(
                    PlannedFilter(
                        table=resolved_table,
                        resolved_column=(
                            resolved_column
                        ),
                        operator=(
                            rule.operator
                        ),
                        value=(
                            rule.rule_value
                        ),
                        confidence=(
                            rule.confidence
                        ),
                        reason=(
                            "Metadata-driven "
                            "business rule: "
                            f"{rule.name} → "
                            f"{resolved_table.entity.name}."
                            f"{column.column_name} "
                            f"{rule.operator} "
                            f"'{rule.rule_value}'."
                        ),
                    )
                )

                matched_rule_ids.add(
                    rule.id
                )

                rule_applied = True
                break

            if rule_applied:
                break

    # --------------------------------------------------
    # 3. Deposit Balance special calculation rule
    #
    # CATEGORY 1011 IS included.
    #
    # But for CATEGORY 1011:
    #
    # WORKINGBALANCE > 0
    #
    # Examples:
    #
    # CATEGORY=1011 BALANCE=25000   -> include
    # CATEGORY=1011 BALANCE=0       -> exclude
    # CATEGORY=1011 BALANCE=-5000   -> exclude
    #
    # Other deposit categories are unaffected.
    #
    # This filter is NOT applied to account counts.
    # --------------------------------------------------

    if deposit_balance_prompt:
        for resolved_table in physical_tables:
            table_name = (
                resolved_table
                .table
                .table_name
                .strip()
                .lower()
            )

            if table_name != "fbnk_account":
                continue

            category_column = None
            working_balance_column = None

            for column in (
                resolved_table.table.columns
            ):
                column_name = normalize_text(
                    column.column_name
                )

                if (
                    column_name
                    == "category"
                ):
                    category_column = column

                elif (
                    column_name
                    == "workingbalance"
                ):
                    working_balance_column = (
                        column
                    )

            # Both physical columns are required for this
            # governed deposit-balance calculation.
            if (
                category_column is None
                or working_balance_column is None
            ):
                continue

            if (
                not category_column.is_discovered
                or not category_column.is_enabled
                or not category_column.ai_access_allowed
                or not working_balance_column.is_discovered
                or not working_balance_column.is_enabled
                or not working_balance_column.ai_access_allowed
            ):
                continue

            resolved_column = (
                ResolvedColumn(
                    column=category_column,
                    confidence=100,
                    matched_terms=[
                        "deposit balance"
                    ],
                )
            )

            filters.append(
                PlannedFilter(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    operator=(
                        "deposit_balance_1011_positive"
                    ),
                    value=None,
                    confidence=100,
                    reason=(
                        "Deposit balance calculation "
                        "rule: CATEGORY 1011 remains "
                        "included but only rows where "
                        "WORKINGBALANCE > 0 contribute "
                        "to deposit balance."
                    ),
                )
            )

            break

    return filters


def determine_aggregation_function(
    intent: str,
    aggregation_terms: list[str],
) -> str | None:
    if intent == "count":
        return "count"

    mapping = {
        "total": "sum",
        "sum": "sum",
        "average": "average",
        "avg": "average",
        "minimum": "minimum",
        "min": "minimum",
        "maximum": "maximum",
        "max": "maximum",
    }

    for term in aggregation_terms:
        normalized = normalize_text(
            term
        )

        if normalized in mapping:
            return mapping[
                normalized
            ]

    if intent in {
        "aggregation",
        "ranking",
    }:
        return "sum"

    return None

def parse_semantic_phrases(
    value: str | None,
) -> list[str]:
    if not value:
        return []

    value = value.strip()

    if not value:
        return []

    # JSON array support
    if value.startswith("["):
        try:
            import json

            parsed = json.loads(value)

            if isinstance(parsed, list):
                return [
                    normalize_text(str(item))
                    for item in parsed
                    if str(item).strip()
                ]
        except Exception:
            pass

    # Fallback for comma-separated values
    return [
        normalize_text(item)
        for item in value.split(",")
        if item.strip()
    ]


def phrase_in_prompt(
    phrase: str,
    prompt: str,
) -> bool:
    phrase = normalize_text(phrase)
    prompt = normalize_text(prompt)

    if not phrase:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(phrase)
        + r"(?![a-z0-9])"
    )

    return (
        re.search(
            pattern,
            prompt,
        )
        is not None
    )

def resolve_semantic_measure(
    database: Session,
    prompt: str,
    physical_tables: list[object],
) -> PlannedAggregation | None:
    normalized_prompt = normalize_text(
        prompt
    )

    measures = list(
        database.scalars(
            select(
                BusinessMeasure
            )
            .where(
                BusinessMeasure.is_active
                .is_(True),
                BusinessMeasure.approval_status
                == "approved",
            )
            .order_by(
                BusinessMeasure.confidence.desc(),
                BusinessMeasure.id.asc(),
            )
        )
    )

    best_measure = None
    best_score = 0

    for measure in measures:
        phrases = [
            normalize_text(
                measure.name
            ),
        ]

        phrases.extend(
            parse_semantic_phrases(
                measure.trigger_phrases
            )
        )

        phrases.extend(
            parse_semantic_phrases(
                measure.synonyms
            )
        )

        phrases = list(
            dict.fromkeys(
                phrase
                for phrase in phrases
                if phrase
            )
        )

        for phrase in phrases:
            if not phrase_in_prompt(
                phrase,
                normalized_prompt,
            ):
                continue

            # Longer phrases are more specific.
            score = (
                len(phrase.split()) * 100
                + len(phrase)
            )

            # Prefer higher-governance confidence
            # when phrases are otherwise similar.
            score += int(
                measure.confidence or 0
            )

            if score > best_score:
                best_score = score
                best_measure = measure

    if best_measure is None:
        return None

    function = normalize_text(
        best_measure.aggregation_function
    )

    # ----------------------------------------------
    # COUNT(*)
    # ----------------------------------------------

    if function == "count":
        return PlannedAggregation(
            function="count",
            table=None,
            resolved_column=None,
            alias=best_measure.name,
            confidence=best_measure.confidence,
        )

    # ----------------------------------------------
    # Column-based measure
    # ----------------------------------------------

    metadata_column_id = (
        best_measure.metadata_column_id
    )

    if metadata_column_id is None:
        return None

    for resolved_table in physical_tables:
        for column in (
            resolved_table.table.columns
        ):
            if (
                column.id
                != metadata_column_id
            ):
                continue

            resolved_column = ResolvedColumn(
                column=column,
                confidence=(
                    best_measure.confidence
                ),
                matched_terms=[
                    best_measure.name
                ],
            )

                    # --------------------------------------------------
        # Context-aware business alias
        # --------------------------------------------------

        measure_alias = (
            best_measure.name
        )

        if (
            function == "sum"
            and (
                "deposit"
                in normalized_prompt.split()
                or "deposits"
                in normalized_prompt.split()
            )
            and normalize_text(
                best_measure.name
            )
            == "account balance"
        ):
            measure_alias = (
                "Deposit Balance"
            )

        return PlannedAggregation(
            function=function,
            table=resolved_table,
            resolved_column=(
                resolved_column
            ),
            alias=measure_alias,
            confidence=(
                best_measure.confidence
            ),
        )

    return None

def resolve_semantic_measures(
    database: Session,
    prompt: str,
    physical_tables: list[object],
) -> list[PlannedAggregation]:
    normalized_prompt = normalize_text(
        prompt
    )

    measures = list(
        database.scalars(
            select(
                BusinessMeasure
            )
            .where(
                BusinessMeasure.is_active
                .is_(True),
                BusinessMeasure.approval_status
                == "approved",
            )
            .order_by(
                BusinessMeasure.confidence.desc(),
                BusinessMeasure.id.asc(),
            )
        )
    )

    matched: list[
        PlannedAggregation
    ] = []

    seen_measure_ids: set[int] = set()

    for measure in measures:
        phrases = [
            normalize_text(
                measure.name
            ),
        ]

        phrases.extend(
            parse_semantic_phrases(
                measure.trigger_phrases
            )
        )

        phrases.extend(
            parse_semantic_phrases(
                measure.synonyms
            )
        )

        phrases = list(
            dict.fromkeys(
                phrase
                for phrase in phrases
                if phrase
            )
        )

        matched_phrase = None

        

        for phrase in phrases:
            # --------------------------------------------------
            # 1. Exact whole-phrase match
            # --------------------------------------------------

            if phrase_in_prompt(
                phrase,
                normalized_prompt,
            ):
                matched_phrase = phrase
                break

            # --------------------------------------------------
            # 2. Flexible semantic token match
            #
            # Allows:
            #
            # "number of accounts"
            #
            # to match:
            #
            # "number and balance of active accounts"
            #
            # Important stop words are ignored.
            # --------------------------------------------------

            phrase_words = {
                word
                for word
                in normalize_text(
                    phrase
                ).split()
                if word
                not in {
                    "of",
                    "the",
                    "a",
                    "an",
                    "by",
                    "for",
                }
            }

            prompt_words = set(
                normalized_prompt.split()
            )

            if (
                len(phrase_words) >= 2
                and phrase_words.issubset(
                    prompt_words
                )
            ):
                matched_phrase = phrase
                break

        if matched_phrase is None:
            continue

        if measure.id in seen_measure_ids:
            continue

        function = normalize_text(
            measure.aggregation_function
        )

        if function == "count":
            matched.append(
                PlannedAggregation(
                    function="count",
                    table=None,
                    resolved_column=None,
                    alias=measure.name,
                    confidence=(
                        measure.confidence
                    ),
                )
            )

            seen_measure_ids.add(
                measure.id
            )

            continue

        metadata_column_id = (
            measure.metadata_column_id
        )

        if metadata_column_id is None:
            continue

        resolved = False

        for resolved_table in physical_tables:
            for column in (
                resolved_table.table.columns
            ):
                if (
                    column.id
                    != metadata_column_id
                ):
                    continue

                resolved_column = (
                    ResolvedColumn(
                        column=column,
                        confidence=(
                            measure.confidence
                        ),
                        matched_terms=[
                            matched_phrase
                        ],
                    )
                )

                measure_alias = (
                    measure.name
                )

                if (
                    function == "sum"
                    and (
                        "deposit"
                        in normalized_prompt.split()
                        or "deposits"
                        in normalized_prompt.split()
                    )
                    and normalize_text(
                        measure.name
                    )
                    == "account balance"
                ):
                    measure_alias = (
                        "Deposit Balance"
                    )

                matched.append(
                    PlannedAggregation(
                        function=function,
                        table=resolved_table,
                        resolved_column=(
                            resolved_column
                        ),
                        alias=measure_alias,
                        confidence=(
                            measure.confidence
                        ),
                    )
                )

                seen_measure_ids.add(
                    measure.id
                )

                resolved = True
                break

            if resolved:
                break

    return matched


def build_aggregation(
    database: Session,
    prompt: str,
    intent: str,
    aggregation_terms: list[str],
    physical_tables: list[object],
    prompt_terms: list[str],
) -> PlannedAggregation | None:

    semantic_measure = (
        resolve_semantic_measure(
            database=database,
            prompt=prompt,
            physical_tables=(
                physical_tables
            ),
        )
    )

    if semantic_measure is not None:
        return semantic_measure

    function = determine_aggregation_function(
        intent=intent,
        aggregation_terms=aggregation_terms,
    )

    normalized_prompt = normalize_text(
        " ".join(
            prompt_terms
        )
    )

    # --------------------------------------------------
    # Explicit measure semantics override generic
    # intent classification.
    #
    # Examples:
    #
    # "active account balance"
    # "inactive account balance"
    # "active account amount"
    # "deposit balance"
    #
    # These are SUM questions even if the upstream
    # intent classifier incorrectly classified them
    # as count.
    # --------------------------------------------------

    explicit_balance_measure = (
        "balance"
        in normalized_prompt.split()
        or "amount"
        in normalized_prompt.split()
    )

    explicit_count_measure = (
        "how many"
        in normalized_prompt
        or "number of"
        in normalized_prompt
        or "count"
        in normalized_prompt.split()
    )

    if (
        explicit_balance_measure
        and not explicit_count_measure
    ):
        function = "sum"

    if function is None:
        return None

    # --------------------------------------------------
    # COUNT
    # --------------------------------------------------

    if function == "count":
        count_alias = (
            "Record Count"
        )

        if (
            "inactive account"
            in normalized_prompt
            or "inactive accounts"
            in normalized_prompt
        ):
            count_alias = (
                "Inactive Account Count"
            )

        elif (
            "active account"
            in normalized_prompt
            or "active accounts"
            in normalized_prompt
        ):
            count_alias = (
                "Active Account Count"
            )

        elif (
            "customer"
            in normalized_prompt
            or "customers"
            in normalized_prompt
        ):
            count_alias = (
                "Customer Count"
            )

        elif (
            "account"
            in normalized_prompt
            or "accounts"
            in normalized_prompt
        ):
            count_alias = (
                "Account Count"
            )

        return PlannedAggregation(
            function="count",
            table=None,
            resolved_column=None,
            alias=count_alias,
            confidence=98,
        )

    # --------------------------------------------------
    # Core Banking balance semantic measure
    #
    # These business questions must always use:
    #
    # FBNK_ACCOUNT.WORKINGBALANCE
    #
    # Examples:
    #
    # total deposit balance
    # total active account balance
    # total inactive account balance
    # active account amount
    # inactive account amount
    #
    # Do not allow generic numeric matching to select
    # VALUE_DATED_BAL or another account balance field.
    # --------------------------------------------------

    is_account_balance_prompt = (
        "account balance"
        in normalized_prompt
        or "account amount"
        in normalized_prompt
        or "deposit balance"
        in normalized_prompt
        or "deposit amount"
        in normalized_prompt
        or "total deposit"
        in normalized_prompt
        or "deposits"
        in normalized_prompt
    )

    if (
        function == "sum"
        and is_account_balance_prompt
    ):
        balance_match = find_best_column(
            physical_tables=physical_tables,
            terms=[
                "working balance",
                "workingbalance",
            ],
            require_numeric=True,
            exclude_primary_key=True,
        )

        if balance_match is not None:
            (
                resolved_table,
                resolved_column,
            ) = balance_match

            column_name = (
                resolved_column
                .column
                .column_name
            )

            if (
                column_name.lower()
                == "workingbalance"
            ):
                aggregation_alias = (
                    "Total Balance"
                )

                if (
                    "inactive account"
                    in normalized_prompt
                    or "inactive accounts"
                    in normalized_prompt
                ):
                    aggregation_alias = (
                        "Inactive Account Balance"
                    )

                elif (
                    "active account"
                    in normalized_prompt
                    or "active accounts"
                    in normalized_prompt
                ):
                    aggregation_alias = (
                        "Active Account Balance"
                    )

                elif (
                    "deposit"
                    in normalized_prompt
                    or "deposits"
                    in normalized_prompt
                ):
                    aggregation_alias = (
                        "Deposit Amount"
                    )

                return PlannedAggregation(
                    function="sum",
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    alias=(
                        aggregation_alias
                    ),
                    confidence=99,
                )

    # --------------------------------------------------
    # Generic aggregation-column resolution
    # --------------------------------------------------

    match = find_best_column(
        physical_tables=physical_tables,
        terms=[
            *prompt_terms,
            *MEASURE_TERMS,
        ],
        require_numeric=True,
        exclude_primary_key=True,
    )

    # --------------------------------------------------
    # No numeric measure found
    # --------------------------------------------------

    if match is None:
        ranking_words = {
            "top",
            "bottom",
            "highest",
            "lowest",
            "largest",
            "smallest",
            "most",
            "least",
        }

        is_ranking = any(
            word in normalized_prompt.split()
            for word in ranking_words
        )

        if is_ranking:
            return None

        if function == "sum":
            count_alias = (
                "Record Count"
            )

            if (
                "inactive account"
                in normalized_prompt
                or "inactive accounts"
                in normalized_prompt
            ):
                count_alias = (
                    "Inactive Account Count"
                )

            elif (
                "active account"
                in normalized_prompt
                or "active accounts"
                in normalized_prompt
            ):
                count_alias = (
                    "Active Account Count"
                )

            elif (
                "customer"
                in normalized_prompt
                or "customers"
                in normalized_prompt
            ):
                count_alias = (
                    "Customer Count"
                )

            elif (
                "account"
                in normalized_prompt
                or "accounts"
                in normalized_prompt
            ):
                count_alias = (
                    "Account Count"
                )

            return PlannedAggregation(
                function="count",
                table=None,
                resolved_column=None,
                alias=count_alias,
                confidence=90,
            )

        return None

    (
        resolved_table,
        resolved_column,
    ) = match

    column_name = (
        resolved_column
        .column
        .column_name
    )

    # --------------------------------------------------
    # Business-friendly aggregation aliases
    # --------------------------------------------------

    aggregation_alias = (
        f"{function}_{column_name}"
    )

    if (
        function == "sum"
        and column_name.lower()
        == "workingbalance"
    ):
        if (
            "inactive account"
            in normalized_prompt
            or "inactive accounts"
            in normalized_prompt
        ):
            aggregation_alias = (
                "Inactive Account Balance"
            )

        elif (
            "active account"
            in normalized_prompt
            or "active accounts"
            in normalized_prompt
        ):
            aggregation_alias = (
                "Active Account Balance"
            )

        elif (
            "current account"
            in normalized_prompt
        ):
            aggregation_alias = (
                "Current Account Balance"
            )

        elif (
            "saving account"
            in normalized_prompt
            or "savings account"
            in normalized_prompt
        ):
            aggregation_alias = (
                "Saving Account Balance"
            )

        elif (
            "deposit"
            in normalized_prompt
            or "deposits"
            in normalized_prompt
        ):
            aggregation_alias = (
                "Deposit Amount"
            )

        else:
            aggregation_alias = (
                "Total Balance"
            )

    return PlannedAggregation(
        function=function,
        table=resolved_table,
        resolved_column=resolved_column,
        alias=aggregation_alias,
        confidence=max(
            80,
            resolved_column.confidence,
        ),
    )

def build_count_alias(
    prompt: str,
) -> str:
    normalized = normalize_text(
        prompt
    )

    if (
        "inactive account"
        in normalized
        or "inactive accounts"
        in normalized
    ):
        return "Inactive Account Count"

    if (
        "active account"
        in normalized
        or "active accounts"
        in normalized
    ):
        return "Active Account Count"

    if (
        "customer"
        in normalized
        or "customers"
        in normalized
    ):
        return "Customer Count"

    if (
        "account"
        in normalized
        or "accounts"
        in normalized
    ):
        return "Account Count"

    return "Record Count"

def apply_high_volume_summary_policy(
    prompt: str,
    physical_tables: list[object],
    aggregation: PlannedAggregation | None,
) -> PlannedAggregation | None:
    normalized = normalize_text(
        prompt
    )

    words = set(
        normalized.split()
    )

    ranking_words = {
        "top",
        "bottom",
        "highest",
        "lowest",
        "largest",
        "smallest",
        "most",
        "least",
    }

    # Ranking queries must keep their
    # existing aggregation logic.
    if words & ranking_words:
        return aggregation

    detail_words = {
        "detail",
        "details",
        "list",
    }

    # Explicit detail request means the user
    # expects rows rather than only a count.
    if words & detail_words:
        return aggregation

    # --------------------------------------------------
    # High-volume entity/table detection
    # --------------------------------------------------

    high_volume_entities = {
        "account",
        "accounts",
        "fbnk account",
        "customer",
        "customers",
        "fbnk customer",
        "transaction",
        "transactions",
    }

    high_volume_tables = {
        "fbnk_account",
        "fbnk_customer",
        "fbnk_transaction",
        "fbnk_stmt_entry",
    }

    matched_high_volume_entity = False

    for resolved_table in physical_tables:
        entity_name = normalize_text(
            resolved_table.entity.name
        )

        table_name = normalize_text(
            resolved_table.table.table_name
        )

        if (
            entity_name
            in high_volume_entities
            or table_name
            in high_volume_tables
        ):
            matched_high_volume_entity = True
            break

    if not matched_high_volume_entity:
        return aggregation

    # --------------------------------------------------
    # Preserve explicit numerical aggregations
    #
    # Example:
    # "Show total deposit balance"
    # should stay SUM(workingbalance),
    # not become COUNT(*).
    # --------------------------------------------------

    if (
        aggregation is not None
        and aggregation.function
        in {
            "sum",
            "average",
            "minimum",
            "maximum",
        }
    ):
        return aggregation

    # --------------------------------------------------
    # Broad high-volume queries default to COUNT.
    #
    # Examples:
    # "Show active accounts"
    # "Show inactive accounts"
    # "Show customers"
    # "Count active accounts"
    # --------------------------------------------------

    return PlannedAggregation(
        function="count",
        table=None,
        resolved_column=None,
        alias=build_count_alias(
            prompt
        ),
        confidence=99,
    )

def resolve_semantic_dimensions(
    database: Session,
    prompt: str,
    physical_tables: list[object],
) -> list[PlannedGrouping]:

    normalized_prompt = normalize_text(
        prompt
    )

    dimensions = list(
        database.scalars(
            select(
                BusinessDimension
            )
            .where(
                BusinessDimension.is_active
                .is_(True),
                BusinessDimension.approval_status
                == "approved",
            )
            .order_by(
                BusinessDimension.confidence.desc(),
                BusinessDimension.id.asc(),
            )
        )
    )

    matched_groupings: list[
        PlannedGrouping
    ] = []

    seen_column_ids: set[int] = set()

    for dimension in dimensions:

        phrases = [
            normalize_text(
                dimension.name
            ),
        ]

        phrases.extend(
            parse_semantic_phrases(
                dimension.trigger_phrases
            )
        )

        phrases.extend(
            parse_semantic_phrases(
                dimension.synonyms
            )
        )

        phrases = list(
            dict.fromkeys(
                phrase
                for phrase in phrases
                if phrase
            )
        )

        matched_phrase = None

        prompt_words = set(
            normalized_prompt.split()
        )

        for phrase in phrases:

            # --------------------------------------------------
            # Exact whole-phrase match
            #
            # Examples:
            # by branch
            # per branch
            # branch wise
            # --------------------------------------------------

            if phrase_in_prompt(
                phrase,
                normalized_prompt,
            ):
                matched_phrase = phrase
                break

            # --------------------------------------------------
            # Flexible semantic dimension matching
            #
            # Allows natural variations while keeping the
            # governed dimension definition as the source
            # of truth.
            # --------------------------------------------------

            phrase_words = {
                word
                for word
                in normalize_text(
                    phrase
                ).split()
                if word
                not in {
                    "by",
                    "per",
                    "each",
                    "the",
                    "a",
                    "an",
                    "wise",
                }
            }

            if (
                phrase_words
                and phrase_words.issubset(
                    prompt_words
                )
            ):
                matched_phrase = phrase
                break

        if matched_phrase is None:
            continue

        metadata_column_id = (
            dimension.metadata_column_id
        )

        if (
            metadata_column_id
            in seen_column_ids
        ):
            continue

        # Find the exact governed physical column
        # represented by this dimension.
        for resolved_table in physical_tables:

            matched = False

            for column in (
                resolved_table.table.columns
            ):
                if (
                    column.id
                    != metadata_column_id
                ):
                    continue

                if (
                    not column.is_discovered
                    or not column.is_enabled
                    or not column.ai_access_allowed
                ):
                    continue

                resolved_column = (
                    ResolvedColumn(
                        column=column,
                        confidence=(
                            dimension.confidence
                        ),
                        matched_terms=[
                            matched_phrase
                        ],
                    )
                )

                matched_groupings.append(
                    PlannedGrouping(
                        table=resolved_table,
                        resolved_column=(
                            resolved_column
                        ),
                        confidence=(
                            dimension.confidence
                        ),
                    )
                )

                seen_column_ids.add(
                    metadata_column_id
                )

                matched = True
                break

            if matched:
                break

    return matched_groupings

def build_group_by(
    database: Session,
    prompt: str,
    physical_tables: list[object],
    aggregation: PlannedAggregation | None,
) -> list[PlannedGrouping]:
    normalized = normalize_text(
        prompt
    )

    # --------------------------------------------------
    # Aggregation is required for grouped summaries.
    # --------------------------------------------------

    if aggregation is None:
        return []

    # --------------------------------------------------
    # 1. Governed semantic dimension catalog
    #
    # This must run BEFORE the old "by ..." parser.
    #
    # Supports natural language such as:
    #
    # by branch
    # per branch
    # branch wise
    # each branch
    #
    # by district
    # per district
    # district wise
    #
    # If the catalog resolves a dimension, use it.
    # --------------------------------------------------

    semantic_groupings = (
        resolve_semantic_dimensions(
            database=database,
            prompt=prompt,
            physical_tables=(
                physical_tables
            ),
        )
    )

    if semantic_groupings:
        return semantic_groupings

    # --------------------------------------------------
    # 2. Existing grouping logic remains as fallback.
    #
    # This protects existing capabilities that are not
    # yet registered in business_dimensions, such as
    # customer, currency, vehicle, etc.
    # --------------------------------------------------

    is_ranking = any(
        term in normalized
        for term in [
            "top ",
            "bottom ",
            "highest",
            "lowest",
            "largest",
            "smallest",
            "most ",
            "least ",
        ]
    )

    # --------------------------------------------------
    # Ranking
    #
    # Examples:
    #
    # Show top 10 branches by deposit balance
    # Show bottom 5 customers by account balance
    # --------------------------------------------------

    if is_ranking:
        ranking_match = re.search(
            r"\b(?:top|bottom)\s+\d+\s+"
            r"([a-z0-9 ]+?)\s+by\s+",
            normalized,
        )

        if not ranking_match:
            return []

        dimension_phrase = (
            ranking_match
            .group(1)
            .strip()
        )

        normalized_dimension = (
            normalize_text(
                dimension_phrase
            )
        )

        dimension_match = None

        # --------------------------------------------------
        # Vehicle ranking
        # --------------------------------------------------

        if (
            "vehicle"
            in normalized_dimension
        ):
            dimension_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "plate number",
                        "plate no",
                        "plate_no",
                    ],
                )
            )

        # --------------------------------------------------
        # Branch ranking
        # --------------------------------------------------

        elif (
            "branch"
            in normalized_dimension
        ):
            dimension_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "branch name",
                        "companyname_1",
                    ],
                )
            )

        # --------------------------------------------------
        # District ranking
        # --------------------------------------------------

        elif (
            "district"
            in normalized_dimension
        ):
            dimension_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "district name",
                        "district_name",
                    ],
                    preferred_entity_terms=[
                        "f eb district",
                        "district",
                        "districts",
                    ],
                )
            )

        # --------------------------------------------------
        # Customer ranking
        # --------------------------------------------------

        elif (
            "customer"
            in normalized_dimension
        ):
            dimension_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "customer name",
                        "short name",
                        "short_name",
                    ],
                )
            )

        # --------------------------------------------------
        # Currency ranking
        # --------------------------------------------------

        elif (
            "currency"
            in normalized_dimension
            or "currencies"
            in normalized_dimension
        ):
            dimension_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "currency",
                    ],
                )
            )

        # --------------------------------------------------
        # Generic ranking dimension
        # --------------------------------------------------

        else:
            dimension_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        dimension_phrase
                    ],
                )
            )

        if dimension_match is None:
            return []

        (
            resolved_table,
            resolved_column,
        ) = dimension_match

        return [
            PlannedGrouping(
                table=resolved_table,
                resolved_column=(
                    resolved_column
                ),
                confidence=98,
            )
        ]

    # --------------------------------------------------
    # 3. Traditional "by ..." grouping fallback
    #
    # Example:
    #
    # Show total deposit balance by branch
    # --------------------------------------------------

    match = re.search(
        r"\bby\s+([a-z0-9 ]+)",
        normalized,
    )

    if not match:
        return []

    phrase = (
        match
        .group(1)
        .strip()
    )

    phrase = re.split(
        r"\b(?:this|last|next|where|with|for|top|bottom|order|limit)\b",
        phrase,
    )[0].strip()

    if not phrase:
        return []

    normalized_phrase = (
        normalize_text(
            phrase
        )
    )

    # --------------------------------------------------
    # Branch grouping
    # --------------------------------------------------

    if normalized_phrase in {
        "branch",
        "branches",
    }:
        branch_match = (
            find_best_column(
                physical_tables=(
                    physical_tables
                ),
                terms=[
                    "branch name",
                    "companyname_1",
                ],
            )
        )

        if branch_match is not None:
            (
                resolved_table,
                resolved_column,
            ) = branch_match

            return [
                PlannedGrouping(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    confidence=99,
                )
            ]

    # --------------------------------------------------
    # District grouping
    #
    # Always use District Name, not RECID/code.
    # --------------------------------------------------

    if normalized_phrase in {
        "district",
        "districts",
    }:
        district_match = (
            find_best_column(
                physical_tables=(
                    physical_tables
                ),
                terms=[
                    "district name",
                    "district_name",
                ],
                preferred_entity_terms=[
                    "f eb district",
                    "district",
                    "districts",
                ],
            )
        )

        if district_match is not None:
            (
                resolved_table,
                resolved_column,
            ) = district_match

            return [
                PlannedGrouping(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    confidence=99,
                )
            ]

    # --------------------------------------------------
    # Customer grouping
    #
    # Always prefer Customer Name.
    # --------------------------------------------------

    if normalized_phrase in {
        "customer",
        "customers",
    }:
        customer_match = (
            find_best_column(
                physical_tables=(
                    physical_tables
                ),
                terms=[
                    "customer name",
                    "short name",
                    "short_name",
                ],
            )
        )

        if customer_match is not None:
            (
                resolved_table,
                resolved_column,
            ) = customer_match

            return [
                PlannedGrouping(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    confidence=99,
                )
            ]

    # --------------------------------------------------
    # Currency grouping
    # --------------------------------------------------

    if normalized_phrase in {
        "currency",
        "currencies",
    }:
        currency_match = (
            find_best_column(
                physical_tables=(
                    physical_tables
                ),
                terms=[
                    "currency",
                ],
            )
        )

        if currency_match is not None:
            (
                resolved_table,
                resolved_column,
            ) = currency_match

            return [
                PlannedGrouping(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    confidence=99,
                )
            ]

    # --------------------------------------------------
    # Generic grouping fallback
    # --------------------------------------------------

    column_match = (
        find_best_column(
            physical_tables=(
                physical_tables
            ),
            terms=(
                phrase.split()[:5]
            ),
        )
    )

    if column_match is None:
        return []

    (
        resolved_table,
        resolved_column,
    ) = column_match

    return [
        PlannedGrouping(
            table=resolved_table,
            resolved_column=(
                resolved_column
            ),
            confidence=88,
        )
    ]

def build_ordering(
    prompt: str,
    intent: str,
    aggregation: PlannedAggregation | None,
    filters: list[PlannedFilter],
    physical_tables: list[object],
) -> list[PlannedSort]:
    normalized = normalize_text(
        prompt
    )

    words = set(
        normalized.split()
    )

    ranking_words = {
        "top",
        "bottom",
        "highest",
        "lowest",
        "largest",
        "smallest",
        "most",
        "least",
    }

    is_ranking = bool(
        words & ranking_words
    )

    # --------------------------------------------------
    # Normal branch grouping
    #
    # Example:
    # "Show total deposit balance by branch"
    #
    # Sort alphabetically by Branch Name.
    #
    # Do NOT apply this to ranking queries.
    # --------------------------------------------------

    if (
        not is_ranking
        and (
            "by branch" in normalized
            or "by branches" in normalized
        )
    ):
        branch_match = (
            find_best_column(
                physical_tables=(
                    physical_tables
                ),
                terms=[
                    "branch name",
                    "companyname_1",
                ],
            )
        )

        if branch_match is not None:
            (
                resolved_table,
                resolved_column,
            ) = branch_match

            return [
                PlannedSort(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    direction="asc",
                    confidence=99,
                )
            ]

    # --------------------------------------------------
    # Aggregation / ranking direction
    #
    # Default aggregated business ranking:
    # DESC
    #
    # Explicit bottom/lowest:
    # ASC
    # --------------------------------------------------

    direction = "desc"

    normalized_for_sort = normalize_text(
        prompt
    )

    if (
        "highest to lowest"
        in normalized_for_sort
        or "largest to smallest"
        in normalized_for_sort
        or "descending"
        in normalized_for_sort
    ):
        direction = "desc"

    elif (
        "lowest to highest"
        in normalized_for_sort
        or "smallest to largest"
        in normalized_for_sort
        or "ascending"
        in normalized_for_sort
    ):
        direction = "asc"

    elif (
        "top" in words
        or "highest" in words
        or "largest" in words
        or "most" in words
    ):
        direction = "desc"

    elif (
        "bottom" in words
        or "lowest" in words
        or "smallest" in words
        or "least" in words
    ):
        direction = "asc"

    # --------------------------------------------------
    # Aggregated / ranked query
    #
    # Example:
    # "Show top 10 branches by deposit balance"
    #
    # ORDER BY SUM(WORKINGBALANCE) DESC
    # --------------------------------------------------

    if (
        aggregation is not None
        and aggregation.resolved_column
        is not None
        and intent
        in {
            "aggregation",
            "ranking",
        }
    ):
        return [
            PlannedSort(
                table=(
                    aggregation.table
                ),
                resolved_column=(
                    aggregation
                    .resolved_column
                ),
                direction=direction,
                confidence=92,
            )
        ]

    # --------------------------------------------------
    # Date-filtered detail queries
    # --------------------------------------------------

    for planned_filter in filters:
        column = (
            planned_filter
            .resolved_column
            .column
        )

        if is_date_type(
            column.data_type
        ):
            return [
                PlannedSort(
                    table=(
                        planned_filter.table
                    ),
                    resolved_column=(
                        planned_filter
                        .resolved_column
                    ),
                    direction="asc",
                    confidence=88,
                )
            ]

    # --------------------------------------------------
    # Trend queries
    # --------------------------------------------------

    if intent == "trend":
        match = find_best_column(
            physical_tables=(
                physical_tables
            ),
            terms=[
                "date",
                "month",
                "year",
                "period",
            ],
            require_date=True,
        )

        if match is not None:
            (
                resolved_table,
                resolved_column,
            ) = match

            return [
                PlannedSort(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    direction="asc",
                    confidence=88,
                )
            ]

    return []

def build_ordering(
    prompt: str,
    intent: str,
    aggregation: PlannedAggregation | None,
    filters: list[PlannedFilter],
    physical_tables: list[object],
) -> list[PlannedSort]:
    normalized = normalize_text(
        prompt
    )

    direction = "desc"

    # --------------------------------------------------
    # Explicit sort phrases must be checked first.
    #
    # "highest to lowest" contains the word "lowest",
    # so checking "lowest" first would incorrectly
    # produce ASC.
    # --------------------------------------------------

    if (
        "highest to lowest" in normalized
        or "largest to smallest" in normalized
        or "descending" in normalized
        or "desc " in normalized
    ):
        direction = "desc"

    elif (
        "lowest to highest" in normalized
        or "smallest to largest" in normalized
        or "ascending" in normalized
        or "asc " in normalized
    ):
        direction = "asc"

    # --------------------------------------------------
    # Ranking words
    # --------------------------------------------------

    elif (
        "top " in normalized
        or "highest" in normalized
        or "largest" in normalized
        or "most " in normalized
    ):
        direction = "desc"

    elif (
        "bottom " in normalized
        or "lowest" in normalized
        or "smallest" in normalized
        or "least " in normalized
    ):
        direction = "asc"

    # --------------------------------------------------
    # Business-facing alphabetical ordering
    #
    # Example:
    # "Show total deposit balance by branch"
    #
    # Normal grouped branch reports should be ordered
    # alphabetically by Branch Name.
    #
    # Ranking queries such as:
    # "Top 10 branches by deposit"
    # must continue ordering by the aggregation value.
    # --------------------------------------------------

    ranking_words = {
        "top",
        "bottom",
        "highest",
        "lowest",
        "largest",
        "smallest",
        "most",
        "least",
    }

    is_ranking = any(
        word in normalized.split()
        for word in ranking_words
    )

    

    # --------------------------------------------------
    # Aggregated business reports
    #
    # Any grouped numeric aggregation should normally
    # be ordered by the aggregated measure.
    #
    # Examples:
    #
    # deposit balance by district
    # -> SUM(balance) DESC
    #
    # deposit balance by branch
    # -> SUM(balance) DESC
    #
    # bottom 5 districts
    # -> SUM(balance) ASC
    # --------------------------------------------------

    if (
        aggregation is not None
        and aggregation.resolved_column
        is not None
        and intent != "trend"
    ):
        return [
            PlannedSort(
                table=(
                    aggregation.table
                ),
                resolved_column=(
                    aggregation
                    .resolved_column
                ),
                direction=direction,
                confidence=95,
            )
        ]

    # --------------------------------------------------
    # Date-filtered detail queries
    #
    # Preserve chronological ordering.
    # --------------------------------------------------

    for planned_filter in filters:
        column = (
            planned_filter
            .resolved_column
            .column
        )

        if is_date_type(
            column.data_type
        ):
            return [
                PlannedSort(
                    table=(
                        planned_filter.table
                    ),
                    resolved_column=(
                        planned_filter
                        .resolved_column
                    ),
                    direction="asc",
                    confidence=88,
                )
            ]

    # --------------------------------------------------
    # Trend queries
    #
    # Trends should always be chronological.
    # --------------------------------------------------

    if intent == "trend":
        match = find_best_column(
            physical_tables=(
                physical_tables
            ),
            terms=[
                "date",
                "month",
                "year",
                "period",
            ],
            require_date=True,
        )

        if match:
            (
                resolved_table,
                resolved_column,
            ) = match

            return [
                PlannedSort(
                    table=resolved_table,
                    resolved_column=(
                        resolved_column
                    ),
                    direction="asc",
                    confidence=88,
                )
            ]

    return []


def evaluate_classifications(
    plan: GovernedPlan,
    user_role: str,
) -> None:
    allowed = (
        ROLE_ALLOWED_CLASSIFICATIONS.get(
            user_role,
            {
                "public",
                "internal",
            },
        )
    )

    blocked_entities = []

    for entity_match in plan.reasoning_result[
        "matched_entities"
    ]:
        entity = entity_match.entity

        if (
            entity.classification
            not in allowed
        ):
            blocked_entities.append(
                entity.name
            )

    passed = not blocked_entities

    add_governance_check(
        plan=plan,
        rule_code="CLASSIFICATION_001",
        passed=passed,
        severity="critical",
        message=(
            "Entity classifications are permitted."
            if passed
            else (
                f"Role '{user_role}' may not access: "
                + ", ".join(
                    blocked_entities
                )
                + "."
            )
        ),
    )


def evaluate_sensitive_columns(
    plan: GovernedPlan,
    user_role: str,
) -> None:
    sensitive_columns = [
        item
        for item in plan.selected_columns
        if (
            item.resolved_column
            .column
            .is_sensitive
        )
    ]

    if not sensitive_columns:
        add_governance_check(
            plan=plan,
            rule_code="SENSITIVE_001",
            passed=True,
            severity="info",
            message=(
                "No sensitive columns are selected."
            ),
        )

        return

    allowed = (
        user_role
        in SENSITIVE_COLUMN_ROLES
    )

    names = ", ".join(
        item.resolved_column
        .column
        .business_name
        or item.resolved_column
        .column
        .column_name
        for item in sensitive_columns
    )

    add_governance_check(
        plan=plan,
        rule_code="SENSITIVE_001",
        passed=allowed,
        severity="critical",
        message=(
            (
                f"Role '{user_role}' may access "
                f"sensitive columns: {names}."
            )
            if allowed
            else (
                f"Role '{user_role}' may not access "
                f"sensitive columns: {names}."
            )
        ),
    )


def load_approved_join_mappings(
    database: Session,
    relationship_ids: set[int],
) -> dict[
    int,
    BusinessRelationshipJoinMapping,
]:
    if not relationship_ids:
        return {}

    statement = (
        select(
            BusinessRelationshipJoinMapping
        )
        .options(
            joinedload(
                BusinessRelationshipJoinMapping.source_table
            ),
            joinedload(
                BusinessRelationshipJoinMapping.source_column
            ),
            joinedload(
                BusinessRelationshipJoinMapping.target_table
            ),
            joinedload(
                BusinessRelationshipJoinMapping.target_column
            ),
        )
        .where(
            BusinessRelationshipJoinMapping.relationship_id.in_(
                relationship_ids
            ),
            BusinessRelationshipJoinMapping.approval_status
            == "approved",
            BusinessRelationshipJoinMapping.is_active.is_(True),
        )
    )

    mappings = list(
        database.scalars(
            statement
        ).unique().all()
    )

    return {
        mapping.relationship_id: mapping
        for mapping in mappings
    }

    

def evaluate_physical_join_readiness(
    plan: GovernedPlan,
    database: Session,
) -> dict[
    int,
    BusinessRelationshipJoinMapping,
]:
    paths = plan.reasoning_result[
        "relationship_paths"
    ]

    physical_tables = plan.reasoning_result[
        "physical_tables"
    ]

    if len(physical_tables) <= 1:
        add_governance_check(
            plan=plan,
            rule_code="JOIN_001",
            passed=True,
            severity="info",
            message=(
                "The plan does not require a "
                "physical database join."
            ),
        )

        return {}

    if not paths:
        add_governance_check(
            plan=plan,
            rule_code="JOIN_001",
            passed=False,
            severity="critical",
            message=(
                "Multiple physical tables were resolved, "
                "but no approved semantic relationship "
                "path connects them."
            ),
        )

        return {}

    relationship_ids = {
        step.relationship.id
        for path in paths
        for step in path.steps
    }

    join_mappings = load_approved_join_mappings(
        database=database,
        relationship_ids=relationship_ids,
    )

    missing_relationship_ids = (
        relationship_ids
        - set(join_mappings.keys())
    )

    if missing_relationship_ids:
        add_governance_check(
            plan=plan,
            rule_code="JOIN_001",
            passed=False,
            severity="critical",
            message=(
                "One or more semantic relationships "
                "do not have an approved physical "
                "join-column mapping."
            ),
        )

        return join_mappings

    data_source_ids = {
        resolved_table.table.data_source_id
        for resolved_table in physical_tables
    }

    if len(data_source_ids) > 1:
        add_governance_check(
            plan=plan,
            rule_code="JOIN_002",
            passed=False,
            severity="critical",
            message=(
                "The current SQL compiler cannot join "
                "tables across different data sources."
            ),
        )

        return join_mappings

    add_governance_check(
        plan=plan,
        rule_code="JOIN_001",
        passed=True,
        severity="info",
        message=(
            "All required semantic relationships "
            "have approved physical join mappings."
        ),
    )

    return join_mappings


def calculate_plan_confidence(
    plan: GovernedPlan,
) -> int:
    components = [
        plan.reasoning_result[
            "overall_confidence"
        ],
    ]

    if plan.selected_columns:
        components.append(
            round(
                sum(
                    item.confidence
                    for item
                    in plan.selected_columns
                )
                / len(
                    plan.selected_columns
                )
            )
        )

    if plan.filters:
        components.append(
            round(
                sum(
                    item.confidence
                    for item
                    in plan.filters
                )
                / len(plan.filters)
            )
        )

    if plan.aggregation:
        components.append(
            plan.aggregation.confidence
        )

    if plan.group_by:
        components.append(
            round(
                sum(
                    item.confidence
                    for item
                    in plan.group_by
                )
                / len(plan.group_by)
            )
        )

    return round(
        sum(components)
        / len(components)
    )


def build_expiry_filters(
    prompt: str,
    physical_tables: list[object],
) -> list[PlannedFilter]:
    normalized = normalize_text(
        prompt
    )

    expired_words = {
        "expired",
        "expire",
        "expires",
        "expiring",
    }

    if not any(
        word in normalized.split()
        for word in expired_words
    ):
        return []

    # If a time period was supplied, such as
    # "expires this month", build_time_filters()
    # already handles the date range.
    if any(
        phrase in normalized
        for phrase in {
            "this month",
            "this week",
            "this year",
            "next month",
            "next week",
            "next year",
        }
    ):
        return []

    terms = [
        "expiry date",
        "expiration date",
        "license expiry date",
        "insurance expiry date",
        "expiry",
        "expiration",
    ]

    match = find_best_column(
        physical_tables=physical_tables,
        terms=terms,
        require_date=True,
    )

    if match is None:
        return []

    (
        resolved_table,
        resolved_column,
    ) = match

    from datetime import date

    return [
        PlannedFilter(
            table=resolved_table,
            resolved_column=(
                resolved_column
            ),
            operator="<",
            value=date.today().isoformat(),
            confidence=94,
            reason=(
                "Expired records were mapped "
                f"to {resolved_column.column.column_name} "
                "before today's date."
            ),
        )
    ]

def create_governed_query_plan(
    database: Session,
    prompt: str,
    domain_id: int | None,
    requested_limit: int,
    maximum_entities: int,
    maximum_path_depth: int,
    user_role: str,
) -> GovernedPlan:
    reasoning_result = (
        analyze_relationship_reasoning(
            database=database,
            prompt=prompt,
            requested_domain_id=domain_id,
            maximum_entities=maximum_entities,
            maximum_path_depth=(
                maximum_path_depth
            ),
        )
    )

    extraction_result = (
        extract_entities(
            prompt
        )
    )

    plan = GovernedPlan(
        decision="blocked",
        is_allowed=False,
        prompt=prompt,
        normalized_prompt=(
            reasoning_result[
                "normalized_prompt"
            ]
        ),
        intent=reasoning_result[
            "intent"
        ],
        reasoning_result=(
            reasoning_result
        ),
    )

    # --------------------------------------------------
    # Read-only governance
    # --------------------------------------------------

    read_only = not any(
        "read-only"
        in warning.lower()
        or "prohibited"
        in warning.lower()
        for warning
        in reasoning_result[
            "warnings"
        ]
    )

    add_governance_check(
        plan=plan,
        rule_code="READ_ONLY_001",
        passed=read_only,
        severity="critical",
        message=(
            "The request complies with the "
            "read-only policy."
            if read_only
            else (
                "The request violates the "
                "read-only policy."
            )
        ),
    )

    if not read_only:
        return plan

    # --------------------------------------------------
    # Physical tables
    # --------------------------------------------------

    physical_tables = (
        reasoning_result[
            "physical_tables"
        ]
    )

    has_tables = bool(
        physical_tables
    )

    add_governance_check(
        plan=plan,
        rule_code="TABLE_001",
        passed=has_tables,
        severity="critical",
        message=(
            "Approved physical table mappings "
            "were resolved."
            if has_tables
            else (
                "No approved physical table "
                "mapping was resolved."
            )
        ),
    )

    if not has_tables:
        plan.warnings.extend(
            reasoning_result[
                "warnings"
            ]
        )

        return plan

    # --------------------------------------------------
    # Display columns
    # --------------------------------------------------

    plan.selected_columns = (
        choose_display_columns(
            physical_tables
        )
    )

    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    plan.filters.extend(
        build_time_filters(
            prompt=prompt,
            physical_tables=physical_tables,
            time_expressions=(
                extraction_result[
                    "time_expressions"
                ]
            ),
        )
    )

    plan.filters.extend(
        build_expiry_filters(
            prompt=prompt,
            physical_tables=physical_tables,
        )
    )

    plan.filters.extend(
        build_status_filters(
            prompt=prompt,
            physical_tables=physical_tables,
            status_terms=(
                extraction_result[
                    "status_terms"
                ]
            ),
        )
    )

    plan.filters.extend(
        build_attribute_filters(
            database=database,
            prompt=prompt,
            physical_tables=physical_tables,
        )
    )

    # --------------------------------------------------
    # Aggregation
    # --------------------------------------------------

    plan.aggregation = (
    build_aggregation(
        database=database,
        prompt=prompt,
        intent=(
            reasoning_result[
                "intent"
            ]
        ),
        aggregation_terms=(
            extraction_result[
                "aggregation_terms"
            ]
        ),
        physical_tables=(
            physical_tables
        ),
        prompt_terms=(
            extraction_result[
                "keywords"
            ]
        ),
    )
)

        # --------------------------------------------------
    # Multi-measure semantic resolution
    #
    # Example:
    # "Show number and balance of active accounts
    #  by district"
    #
    # -> Account Count
    # -> Account Balance
    # --------------------------------------------------

    semantic_aggregations = (
        resolve_semantic_measures(
            database=database,
            prompt=prompt,
            physical_tables=(
                physical_tables
            ),
        )
    )

    if len(
        semantic_aggregations
    ) > 1:
        plan.aggregations = (
            semantic_aggregations
        )

    plan.aggregation = (
        apply_high_volume_summary_policy(
            prompt=prompt,
            physical_tables=(
                physical_tables
            ),
            aggregation=(
                plan.aggregation
            ),
        )
    )

    # --------------------------------------------------
    # Grouping
    # --------------------------------------------------

    plan.group_by = (
    build_group_by(
        database=database,
        prompt=prompt,
        physical_tables=(
            physical_tables
        ),
        aggregation=(
            plan.aggregation
        ),
    )
)

        # --------------------------------------------------
    # Rich Core Banking account reports
    #
    # Examples:
    #
    # "Show active account report by branch"
    # "Show inactive account report by branch"
    #
    # Output:
    # Branch Name
    # District Name
    # Account Count
    # Account Balance
    # --------------------------------------------------

    normalized_report_prompt = normalize_text(
        prompt
    )

    is_account_report = (
        "account report"
        in normalized_report_prompt
    )

    if is_account_report:
        # --------------------------------------------------
        # Find FBNK_ACCOUNT for measures
        # --------------------------------------------------

        account_table = None

        for resolved_table in physical_tables:
            if (
                normalize_text(
                    resolved_table.table.table_name
                )
                == "fbnk account"
            ):
                account_table = resolved_table
                break

        # --------------------------------------------------
        # Find WORKINGBALANCE
        # --------------------------------------------------

        working_balance_match = (
            find_best_column(
                physical_tables=physical_tables,
                terms=[
                    "working balance",
                    "workingbalance",
                ],
                require_numeric=True,
                exclude_primary_key=True,
            )
        )

        # --------------------------------------------------
        # Determine account status labels
        # --------------------------------------------------

        if (
            "inactive account"
            in normalized_report_prompt
            or "inactive accounts"
            in normalized_report_prompt
        ):
            count_alias = (
                "Inactive Account Count"
            )

            balance_alias = (
                "Inactive Account Balance"
            )

        else:
            count_alias = (
                "Active Account Count"
            )

            balance_alias = (
                "Active Account Balance"
            )

        # --------------------------------------------------
        # Build report measures
        # --------------------------------------------------

        plan.aggregations = []

        plan.aggregations.append(
            PlannedAggregation(
                function="count",
                table=None,
                resolved_column=None,
                alias=count_alias,
                confidence=99,
            )
        )

        if working_balance_match is not None:
            (
                balance_table,
                balance_column,
            ) = working_balance_match

            plan.aggregations.append(
                PlannedAggregation(
                    function="sum",
                    table=balance_table,
                    resolved_column=(
                        balance_column
                    ),
                    alias=balance_alias,
                    confidence=99,
                )
            )

        # --------------------------------------------------
        # Rich branch report dimensions
        #
        # Branch Name + District Name
        # --------------------------------------------------

        if (
            "by branch"
            in normalized_report_prompt
            or "by branches"
            in normalized_report_prompt
        ):
            report_groupings: list[
                PlannedGrouping
            ] = []

            branch_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "branch name",
                        "companyname_1",
                    ],
                )
            )

            district_match = (
                find_best_column(
                    physical_tables=(
                        physical_tables
                    ),
                    terms=[
                        "district name",
                        "district_name",
                    ],
                )
            )

            if branch_match is not None:
                (
                    branch_table,
                    branch_column,
                ) = branch_match

                report_groupings.append(
                    PlannedGrouping(
                        table=branch_table,
                        resolved_column=(
                            branch_column
                        ),
                        confidence=99,
                    )
                )

            if district_match is not None:
                (
                    district_table,
                    district_column,
                ) = district_match

                report_groupings.append(
                    PlannedGrouping(
                        table=district_table,
                        resolved_column=(
                            district_column
                        ),
                        confidence=99,
                    )
                )

            if report_groupings:
                plan.group_by = (
                    report_groupings
                )

    # --------------------------------------------------
    # Ordering
    # --------------------------------------------------

    plan.order_by = (
        build_ordering(
            prompt=prompt,
            intent=(
                reasoning_result[
                    "intent"
                ]
            ),
            aggregation=(
                plan.aggregation
            ),
            filters=(
                plan.filters
            ),
            physical_tables=(
                physical_tables
            ),
        )
    )

    # --------------------------------------------------
    # Result limit policy
    # --------------------------------------------------

    role_limit = (
        ROLE_ROW_LIMITS.get(
            user_role,
            100,
        )
    )

    is_grouped_summary = (
        plan.aggregation is not None
        and bool(
            plan.group_by
        )
    )

    if is_grouped_summary:
        explicit_limit_match = (
            re.search(
                r"\b(?:top|bottom|first|last)"
                r"\s+(\d+)\b",
                normalize_text(
                    prompt
                ),
            )
        )

        if explicit_limit_match:
            plan.approved_limit = (
                min(
                    max(
                        int(
                            explicit_limit_match
                            .group(1)
                        ),
                        1,
                    ),
                    1000,
                )
            )

        else:
            plan.approved_limit = 1000

    else:
        plan.approved_limit = (
            detect_requested_limit(
                prompt=prompt,
                requested_limit=(
                    requested_limit
                ),
                role_limit=(
                    role_limit
                ),
            )
        )

    # --------------------------------------------------
    # Row limit governance
    # --------------------------------------------------

    if is_grouped_summary:
        add_governance_check(
            plan=plan,
            rule_code="ROW_LIMIT_001",
            passed=True,
            severity="info",
            message=(
                "Grouped summary results may "
                "return up to "
                f"{plan.approved_limit} groups."
            ),
        )

    elif requested_limit > role_limit:
        add_governance_check(
            plan=plan,
            rule_code="ROW_LIMIT_001",
            passed=False,
            severity="warning",
            message=(
                f"Requested limit "
                f"{requested_limit} was reduced "
                f"to {role_limit} for role "
                f"'{user_role}'."
            ),
        )

    else:
        add_governance_check(
            plan=plan,
            rule_code="ROW_LIMIT_001",
            passed=True,
            severity="info",
            message=(
                f"Result limit "
                f"{plan.approved_limit} "
                "is permitted."
            ),
        )

    # --------------------------------------------------
    # Classification governance
    # --------------------------------------------------

    evaluate_classifications(
        plan=plan,
        user_role=user_role,
    )

    evaluate_sensitive_columns(
        plan=plan,
        user_role=user_role,
    )

    # --------------------------------------------------
    # Physical join governance
    # --------------------------------------------------

    join_mappings = (
        evaluate_physical_join_readiness(
            plan=plan,
            database=database,
        )
    )

    plan.join_mappings = (
        join_mappings
    )

    # --------------------------------------------------
    # Confidence
    # --------------------------------------------------

    plan.overall_confidence = (
        calculate_plan_confidence(
            plan
        )
    )

    confidence_passed = (
        plan.overall_confidence
        >= 75
    )

    add_governance_check(
        plan=plan,
        rule_code="CONFIDENCE_001",
        passed=(
            confidence_passed
        ),
        severity="warning",
        message=(
            (
                f"Plan confidence is sufficient "
                f"({plan.overall_confidence}%)."
            )
            if confidence_passed
            else (
                f"Plan confidence is only "
                f"{plan.overall_confidence}%."
            )
        ),
    )

    # --------------------------------------------------
    # Warnings / explanation
    # --------------------------------------------------

    plan.warnings.extend(
        reasoning_result[
            "warnings"
        ]
    )

    plan.explanation.extend(
        reasoning_result[
            "explanation"
        ]
    )

    plan.explanation.append(
        (
            f"The governed planner selected "
            f"{len(plan.selected_columns)} "
            f"approved column(s)."
        )
    )

    if plan.filters:
        plan.explanation.append(
            (
                f"The planner created "
                f"{len(plan.filters)} filter(s)."
            )
        )

    if plan.aggregation:
        plan.explanation.append(
            (
                "Aggregation selected: "
                f"{plan.aggregation.function}."
            )
        )

    if plan.group_by:
        plan.explanation.append(
            (
                f"The planner created "
                f"{len(plan.group_by)} "
                "grouping dimension(s)."
            )
        )

    # --------------------------------------------------
    # Critical governance failures
    # --------------------------------------------------

    critical_failures = [
        check
        for check
        in plan.governance_checks
        if (
            not check.passed
            and check.severity
            == "critical"
        )
    ]

    if critical_failures:
        plan.decision = "blocked"
        plan.is_allowed = False

        return plan

    # --------------------------------------------------
    # Clarification
    # --------------------------------------------------

    requires_clarification = (
        reasoning_result[
            "requires_clarification"
        ]
        or plan.overall_confidence
        < 75
    )

    if requires_clarification:
        plan.decision = (
            "requires_clarification"
        )

        plan.is_allowed = False

        return plan

    # --------------------------------------------------
    # Approved
    # --------------------------------------------------

    plan.decision = "approved"
    plan.is_allowed = True

    return plan