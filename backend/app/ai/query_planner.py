import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.ai.prompt_pipeline import (
    analyze_prompt_pipeline,
)


NUMERIC_TYPE_TERMS = {
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


DATE_TYPE_TERMS = {
    "date",
    "datetime",
    "timestamp",
    "time",
}


IDENTIFIER_TERMS = {
    "id",
    "identifier",
    "number",
    "code",
    "reference",
    "name",
}


STATUS_TERMS = {
    "status",
    "state",
    "active",
    "inactive",
    "approved",
    "rejected",
    "pending",
    "completed",
    "assigned",
    "available",
}


@dataclass
class PlannedColumn:
    column: object
    purpose: str
    confidence: int


@dataclass
class PlannedFilter:
    column: object
    operator: str
    value: str | int | float | bool | None
    confidence: int
    reason: str


@dataclass
class PlannedAggregation:
    function: str
    column: object | None
    alias: str
    confidence: int


@dataclass
class PlannedSort:
    column: object
    direction: str
    confidence: int


@dataclass
class CandidatePlan:
    position: int
    table_match: object
    intent: str

    selected_columns: list[PlannedColumn] = field(
        default_factory=list
    )

    filters: list[PlannedFilter] = field(
        default_factory=list
    )

    aggregation: PlannedAggregation | None = None

    group_by: list[PlannedColumn] = field(
        default_factory=list
    )

    order_by: list[PlannedSort] = field(
        default_factory=list
    )

    row_limit: int = 100
    confidence: int = 0
    requires_clarification: bool = False

    warnings: list[str] = field(
        default_factory=list
    )

    reasons: list[str] = field(
        default_factory=list
    )


def normalize_text(value: str | None) -> str:
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


def data_type_contains(
    data_type: str,
    expected_terms: set[str],
) -> bool:
    normalized = normalize_text(data_type)

    return any(
        term in normalized
        for term in expected_terms
    )


def is_numeric_column(column: object) -> bool:
    return data_type_contains(
        column.data_type,
        NUMERIC_TYPE_TERMS,
    )


def is_date_column(column: object) -> bool:
    return data_type_contains(
        column.data_type,
        DATE_TYPE_TERMS,
    )


def column_text(column: object) -> str:
    return " ".join(
        value
        for value in [
            normalize_text(
                column.business_name
            ),
            normalize_text(
                column.column_name
            ),
            normalize_text(
                column.description
            ),
        ]
        if value
    )


def find_column_by_terms(
    columns: list[object],
    terms: list[str],
    require_numeric: bool = False,
    require_date: bool = False,
) -> object | None:
    best_column = None
    best_score = 0

    for resolution in columns:
        column = resolution.column

        if require_numeric and not is_numeric_column(
            column
        ):
            continue

        if require_date and not is_date_column(
            column
        ):
            continue

        text = column_text(column)
        score = resolution.score

        for term in terms:
            normalized_term = normalize_text(term)

            if normalized_term and normalized_term in text:
                score += 35

        if score > best_score:
            best_column = column
            best_score = score

    return best_column


def choose_display_columns(
    columns: list[object],
    maximum_columns: int = 8,
) -> list[PlannedColumn]:
    selected: list[PlannedColumn] = []

    for resolution in columns:
        column = resolution.column
        text = column_text(column)

        purpose = "result"

        if column.is_primary_key:
            purpose = "identifier"

        elif any(
            term in text
            for term in IDENTIFIER_TERMS
        ):
            purpose = "identifier"

        elif is_date_column(column):
            purpose = "date"

        elif any(
            term in text
            for term in STATUS_TERMS
        ):
            purpose = "status"

        selected.append(
            PlannedColumn(
                column=column,
                purpose=purpose,
                confidence=resolution.confidence,
            )
        )

        if len(selected) >= maximum_columns:
            break

    return selected


def detect_requested_limit(
    prompt: str,
    default_limit: int,
) -> int:
    normalized = normalize_text(prompt)

    match = re.search(
        r"\btop\s+(\d+)\b",
        normalized,
    )

    if not match:
        match = re.search(
            r"\bbottom\s+(\d+)\b",
            normalized,
        )

    if match:
        return min(
            max(int(match.group(1)), 1),
            1000,
        )

    return default_limit


def create_time_filter(
    time_expression: str,
    columns: list[object],
) -> PlannedFilter | None:
    date_column = find_column_by_terms(
        columns,
        terms=[
            "date",
            "created",
            "transaction",
            "request",
            "expiry",
            "start",
            "end",
        ],
        require_date=True,
    )

    if date_column is None:
        return None

    operator_map = {
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

    operator = operator_map.get(
        time_expression
    )

    if operator is None:
        return None

    return PlannedFilter(
        column=date_column,
        operator=operator,
        value=None,
        confidence=88,
        reason=(
            f"Time expression '{time_expression}' "
            f"was mapped to {date_column.column_name}."
        ),
    )


def create_status_filter(
    status_term: str,
    columns: list[object],
) -> PlannedFilter | None:
    status_column = find_column_by_terms(
        columns,
        terms=[
            status_term,
            "status",
            "state",
            "assigned",
            "available",
            "approval",
        ],
    )

    if status_column is None:
        return None

    return PlannedFilter(
        column=status_column,
        operator="=",
        value=status_term,
        confidence=82,
        reason=(
            f"Status term '{status_term}' "
            f"was mapped to {status_column.column_name}."
        ),
    )


def choose_aggregation(
    intent: str,
    aggregation_terms: list[str],
    columns: list[object],
) -> PlannedAggregation | None:
    if intent == "count":
        return PlannedAggregation(
            function="count",
            column=None,
            alias="record_count",
            confidence=98,
        )

    function_map = {
        "total": "sum",
        "sum": "sum",
        "average": "average",
        "avg": "average",
        "minimum": "minimum",
        "min": "minimum",
        "maximum": "maximum",
        "max": "maximum",
    }

    requested_function = None

    for term in aggregation_terms:
        if term in function_map:
            requested_function = (
                function_map[term]
            )
            break

    if requested_function is None:
        if intent == "aggregation":
            requested_function = "sum"
        else:
            return None

    numeric_column = find_column_by_terms(
        columns,
        terms=[
            "amount",
            "total",
            "balance",
            "quantity",
            "value",
            "price",
        ],
        require_numeric=True,
    )

    if numeric_column is None:
        return None

    alias = (
        f"{requested_function}_"
        f"{numeric_column.column_name}"
    )

    return PlannedAggregation(
        function=requested_function,
        column=numeric_column,
        alias=alias,
        confidence=85,
    )


def choose_group_by(
    prompt: str,
    columns: list[object],
) -> list[PlannedColumn]:
    normalized = normalize_text(prompt)

    match = re.search(
        r"\bby\s+([a-z0-9 ]+)",
        normalized,
    )

    if not match:
        return []

    group_phrase = match.group(1).strip()

    group_terms = group_phrase.split()[:4]

    column = find_column_by_terms(
        columns,
        terms=group_terms,
    )

    if column is None:
        return []

    return [
        PlannedColumn(
            column=column,
            purpose="group_by",
            confidence=82,
        )
    ]


def choose_ordering(
    intent: str,
    aggregation: PlannedAggregation | None,
    columns: list[object],
) -> list[PlannedSort]:
    if intent == "ranking" and aggregation:
        if aggregation.column is not None:
            return [
                PlannedSort(
                    column=aggregation.column,
                    direction="desc",
                    confidence=90,
                )
            ]

    if intent == "expiry_monitoring":
        date_column = find_column_by_terms(
            columns,
            terms=[
                "expiry",
                "expiration",
                "due date",
            ],
            require_date=True,
        )

        if date_column:
            return [
                PlannedSort(
                    column=date_column,
                    direction="asc",
                    confidence=90,
                )
            ]

    return []


def build_candidate_plan(
    position: int,
    table_match: object,
    pipeline_result: dict,
    default_limit: int,
) -> CandidatePlan:
    intent = pipeline_result["intent"]

    plan = CandidatePlan(
        position=position,
        table_match=table_match,
        intent=intent,
        row_limit=detect_requested_limit(
            pipeline_result["prompt"],
            default_limit,
        ),
    )

    plan.selected_columns = (
        choose_display_columns(
            table_match.columns
        )
    )

    for time_expression in pipeline_result[
        "time_expressions"
    ]:
        planned_filter = create_time_filter(
            time_expression,
            table_match.columns,
        )

        if planned_filter:
            plan.filters.append(
                planned_filter
            )
        else:
            plan.warnings.append(
                "A time expression was detected, "
                "but no suitable date column was found."
            )

    for status_term in pipeline_result[
        "status_terms"
    ]:
        planned_filter = create_status_filter(
            status_term,
            table_match.columns,
        )

        if planned_filter:
            plan.filters.append(
                planned_filter
            )
        else:
            plan.warnings.append(
                f"Status term '{status_term}' could "
                "not be mapped to a column."
            )

    plan.aggregation = choose_aggregation(
        intent=intent,
        aggregation_terms=pipeline_result[
            "aggregation_terms"
        ],
        columns=table_match.columns,
    )

    if (
        intent in {
            "aggregation",
            "ranking",
        }
        and plan.aggregation is None
    ):
        plan.warnings.append(
            "The request requires aggregation, "
            "but no suitable numeric column was found."
        )

    plan.group_by = choose_group_by(
        pipeline_result["prompt"],
        table_match.columns,
    )

    plan.order_by = choose_ordering(
        intent=intent,
        aggregation=plan.aggregation,
        columns=table_match.columns,
    )

    confidence_components = [
        table_match.confidence,
        pipeline_result[
            "intent_confidence"
        ],
    ]

    if plan.selected_columns:
        confidence_components.append(
            max(
                column.confidence
                for column
                in plan.selected_columns
            )
        )

    if plan.filters:
        confidence_components.append(
            round(
                sum(
                    item.confidence
                    for item in plan.filters
                )
                / len(plan.filters)
            )
        )

    if plan.aggregation:
        confidence_components.append(
            plan.aggregation.confidence
        )

    plan.confidence = round(
        sum(confidence_components)
        / len(confidence_components)
    )

    plan.requires_clarification = (
        plan.confidence < 80
        or (
            intent
            in {
                "aggregation",
                "ranking",
            }
            and plan.aggregation is None
        )
    )

    plan.reasons.extend(
        table_match.reasons
    )

    plan.reasons.append(
        f"Query intent resolved as {intent}."
    )

    if plan.filters:
        plan.reasons.append(
            f"{len(plan.filters)} filter(s) planned."
        )

    if plan.aggregation:
        plan.reasons.append(
            f"Aggregation planned: "
            f"{plan.aggregation.function}."
        )

    return plan


def create_query_plans(
    database: Session,
    prompt: str,
    data_source_id: int | None,
    maximum_plans: int,
    default_limit: int,
) -> dict:
    pipeline_result = analyze_prompt_pipeline(
        database=database,
        prompt=prompt,
        data_source_id=data_source_id,
        maximum_results=maximum_plans,
    )

    if not pipeline_result["is_safe"]:
        return {
            **pipeline_result,
            "candidate_plans": [],
            "recommended_plan_position": None,
            "requires_user_selection": False,
        }

    candidate_plans = [
        build_candidate_plan(
            position=index,
            table_match=table_match,
            pipeline_result=pipeline_result,
            default_limit=default_limit,
        )
        for index, table_match in enumerate(
            pipeline_result["matched_tables"],
            start=1,
        )
    ]

    recommended_position = (
        candidate_plans[0].position
        if candidate_plans
        else None
    )

    requires_selection = False

    if not candidate_plans:
        requires_selection = True

    elif candidate_plans[0].confidence < 85:
        requires_selection = True

    elif len(candidate_plans) > 1:
        difference = (
            candidate_plans[0].confidence
            - candidate_plans[1].confidence
        )

        if difference < 8:
            requires_selection = True

    return {
        **pipeline_result,
        "candidate_plans": candidate_plans,
        "recommended_plan_position": (
            recommended_position
        ),
        "requires_user_selection": (
            requires_selection
        ),
    }
