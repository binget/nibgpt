import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.ai.governed_query_planner import (
    GovernedPlan,
    PlannedAggregation,
    PlannedColumn,
    PlannedFilter,
    PlannedGrouping,
    PlannedSort,
    create_governed_query_plan,
)
from app.models.data_source import DataSource


SUPPORTED_DIALECTS = {
    "mysql": "mysql",
    "mariadb": "mysql",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "oracle": "oracle",
    "mssql": "mssql",
    "sql server": "mssql",
    "sqlserver": "mssql",
}


@dataclass
class CompiledParameter:
    name: str
    value: Any
    data_type: str


@dataclass
class CompiledTable:
    metadata_table_id: int
    data_source_id: int
    schema_name: str | None
    table_name: str
    alias: str


@dataclass
class CompiledJoin:
    join_mapping_id: int
    relationship_id: int
    join_type: str

    source_table_alias: str
    source_column_name: str

    target_table_alias: str
    target_column_name: str

    expression: str


@dataclass
class CompiledSQL:
    prompt: str
    decision: str
    is_compiled: bool

    dialect: str | None = None
    sql: str | None = None

    parameters: list[
        CompiledParameter
    ] = field(default_factory=list)

    tables: list[
        CompiledTable
    ] = field(default_factory=list)

    joins: list[
        CompiledJoin
    ] = field(default_factory=list)

    approved_limit: int = 0
    overall_confidence: int = 0

    warnings: list[str] = field(
        default_factory=list
    )

    errors: list[str] = field(
        default_factory=list
    )

    explanation: list[str] = field(
        default_factory=list
    )


def normalize_database_type(
    database_type: str | None,
) -> str | None:
    if not database_type:
        return None

    normalized = (
        database_type
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

    return SUPPORTED_DIALECTS.get(
        normalized
    )


def quote_identifier(
    identifier: str,
    dialect: str,
) -> str:
    if not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_$#]*",
        identifier,
    ):
        raise ValueError(
            f"Unsafe SQL identifier: {identifier}"
        )

    if dialect == "mysql":
        return f"`{identifier}`"

    if dialect == "mssql":
        return f"[{identifier}]"

    if dialect == "oracle":
        return identifier.upper()

    return f'"{identifier}"'

def quote_output_alias(
    alias: str,
    dialect: str,
) -> str:
    """
    Safely quote a human-readable SELECT alias.

    Examples:
        Vehicle Number
        Customer Name
        Total Amount
    """

    cleaned = (
        str(alias)
        .replace("\x00", "")
        .strip()
    )

    if not cleaned:
        raise ValueError(
            "SQL output alias cannot be empty."
        )

    if len(cleaned) > 150:
        raise ValueError(
            "SQL output alias is too long."
        )

    if dialect == "mysql":
        cleaned = cleaned.replace(
            "`",
            "``",
        )

        return f"`{cleaned}`"

    if dialect == "mssql":
        cleaned = cleaned.replace(
            "]",
            "]]",
        )

        return f"[{cleaned}]"

    cleaned = cleaned.replace(
        '"',
        '""',
    )

    return f'"{cleaned}"'

def table_alias_clause(
    alias: str,
    dialect: str,
) -> str:
    quoted_alias = quote_identifier(
        alias,
        dialect,
    )

    if dialect == "oracle":
        return quoted_alias

    return f"AS {quoted_alias}"

def qualified_table_name(
    schema_name: str | None,
    table_name: str,
    dialect: str,
) -> str:
    quoted_table = quote_identifier(
        table_name,
        dialect,
    )

    if not schema_name:
        return quoted_table

    return (
        f"{quote_identifier(schema_name, dialect)}."
        f"{quoted_table}"
    )


def column_reference(
    table_alias: str,
    column_name: str,
    dialect: str,
) -> str:
    return (
        f"{quote_identifier(table_alias, dialect)}."
        f"{quote_identifier(column_name, dialect)}"
    )


def parameter_placeholder(
    parameter_name: str,
    dialect: str,
) -> str:
    if dialect == "oracle":
        return f":{parameter_name}"

    return f":{parameter_name}"


def calculate_date_range(
    operator: str,
    value: object = None,
) -> tuple[
    date,
    date,
] | None:
    today = date.today()

    if operator == "this_day":
        return (
            today,
            today + timedelta(days=1),
        )

    if operator == "last_day":
        start = today - timedelta(days=1)

        return (
            start,
            today,
        )

    if operator == "next_day":
        start = today + timedelta(days=1)

        return (
            start,
            start + timedelta(days=1),
        )

    if operator == "this_week":
        start = today - timedelta(
            days=today.weekday()
        )

        return (
            start,
            start + timedelta(days=7),
        )

    if operator == "last_week":
        current_start = (
            today
            - timedelta(
                days=today.weekday()
            )
        )

        start = (
            current_start
            - timedelta(days=7)
        )

        return (
            start,
            current_start,
        )

    if operator == "next_week":
        current_start = (
            today
            - timedelta(
                days=today.weekday()
            )
        )

        start = (
            current_start
            + timedelta(days=7)
        )

        return (
            start,
            start + timedelta(days=7),
        )
        
    if operator == "rolling_months":
        try:
            months = int(value)
        except (TypeError, ValueError):
            return None

        if months < 1 or months > 120:
            return None

        # Rolling calendar periods use completed months.
        # Current incomplete month is excluded.
        end = today.replace(day=1)

        total_months = (
            end.year * 12
            + (end.month - 1)
            - months
        )

        start = date(
            total_months // 12,
            total_months % 12 + 1,
            1,
        )

        return (
            start,
            end,
        )

    if operator == "this_month":
        start = today.replace(day=1)

        if start.month == 12:
            end = start.replace(
                year=start.year + 1,
                month=1,
            )
        else:
            end = start.replace(
                month=start.month + 1
            )

        return start, end

    if operator == "last_month":
        current_start = today.replace(
            day=1
        )

        previous_end = (
            current_start
            - timedelta(days=1)
        )

        start = previous_end.replace(
            day=1
        )

        return (
            start,
            current_start,
        )

    if operator == "next_month":
        current_start = today.replace(
            day=1
        )

        if current_start.month == 12:
            start = current_start.replace(
                year=current_start.year + 1,
                month=1,
            )
        else:
            start = current_start.replace(
                month=current_start.month + 1
            )

        if start.month == 12:
            end = start.replace(
                year=start.year + 1,
                month=1,
            )
        else:
            end = start.replace(
                month=start.month + 1
            )

        return start, end

    if operator == "this_year":
        start = date(
            today.year,
            1,
            1,
        )

        return (
            start,
            date(
                today.year + 1,
                1,
                1,
            ),
        )

    if operator == "last_year":
        return (
            date(
                today.year - 1,
                1,
                1,
            ),
            date(
                today.year,
                1,
                1,
            ),
        )

    if operator == "next_year":
        return (
            date(
                today.year + 1,
                1,
                1,
            ),
            date(
                today.year + 2,
                1,
                1,
            ),
        )

    return None

def time_grain_expression(
    alias: str,
    column: object,
    dialect: str,
    time_grain: str | None,
) -> str:
    reference = column_reference(
        alias,
        column.column_name,
        dialect,
    )

    if time_grain is None:
        return reference

    data_type = (
        column.data_type
        or ""
    ).lower()

    numeric_date = any(
        numeric_type in data_type
        for numeric_type in (
            "number",
            "numeric",
            "decimal",
            "integer",
            "int",
        )
    )

    # --------------------------------------------------
    # Legacy numeric YYYYMMDD dates
    # --------------------------------------------------

    if numeric_date:
        if time_grain == "day":
            return reference

        if time_grain == "month":
            return (
                f"FLOOR({reference} / 100)"
            )

        if time_grain == "year":
            return (
                f"FLOOR({reference} / 10000)"
            )

        if time_grain == "quarter":
            return (
                "CONCAT("
                f"FLOOR({reference} / 10000), "
                "'-Q' || "
                "CEIL("
                f"MOD(FLOOR({reference} / 100), 100) / 3"
                ")"
                ")"
            )

        # Weekly grouping for numeric YYYYMMDD requires
        # conversion to a real date first.
        if time_grain == "week":
            return (
                "TRUNC("
                "TO_DATE("
                f"TO_CHAR({reference}), "
                "'YYYYMMDD'"
                "), "
                "'IW'"
                ")"
            )

    # --------------------------------------------------
    # Native DATE/TIMESTAMP
    # --------------------------------------------------

    if dialect.lower() == "oracle":
        if time_grain == "day":
            return (
                f"TRUNC({reference})"
            )

        if time_grain == "week":
            return (
                f"TRUNC({reference}, 'IW')"
            )

        if time_grain == "month":
            return (
                f"TRUNC({reference}, 'MM')"
            )

        if time_grain == "quarter":
            return (
                f"TRUNC({reference}, 'Q')"
            )

        if time_grain == "year":
            return (
                f"TRUNC({reference}, 'YYYY')"
            )

    return reference

def compile_filter(
    planned_filter: PlannedFilter,
    table_aliases: dict[int, str],
    dialect: str,
    parameter_index: int,
) -> tuple[
    str,
    list[CompiledParameter],
    int,
]:
    table = planned_filter.table.table

    alias = table_aliases[
        table.id
    ]

    column = (
        planned_filter
        .resolved_column
        .column
    )

    reference = column_reference(
        alias,
        column.column_name,
        dialect,
    )
    if (
        planned_filter.operator
        == "deposit_balance_1011_positive"
    ):
        category_reference = column_reference(
            alias,
            "CATEGORY",
            dialect,
        )

        balance_reference = column_reference(
            alias,
            "WORKINGBALANCE",
            dialect,
        )

        return (
            (
                f"({category_reference} <> '1011' "
                f"OR {balance_reference} > 0)"
            ),
            [],
            parameter_index,
        )

    operator = planned_filter.operator

    parameters: list[
        CompiledParameter
    ] = []

    # --------------------------------------------------
    # NULL operators
    # --------------------------------------------------

    if operator == "is_null":
        return (
            f"{reference} IS NULL",
            parameters,
            parameter_index,
        )

    if operator == "is_not_null":
        return (
            f"{reference} IS NOT NULL",
            parameters,
            parameter_index,
        )

    # --------------------------------------------------
    # Date-range operators
    # --------------------------------------------------

    date_range = calculate_date_range(
        operator,
        planned_filter.value,
    )

    if date_range:
        start_value, end_value = (
            date_range
        )

        start_name = (
            f"p{parameter_index}"
        )
        parameter_index += 1

        end_name = (
            f"p{parameter_index}"
        )
        parameter_index += 1

        column_data_type = (
            column.data_type or ""
        ).lower()

        if any(
            numeric_type in column_data_type
            for numeric_type in (
                "number",
                "numeric",
                "decimal",
                "integer",
                "int",
            )
        ):
            # Legacy/Core Banking numeric date storage:
            # YYYYMMDD
            start_parameter_value = int(
                start_value.strftime("%Y%m%d")
            )

            end_parameter_value = int(
                end_value.strftime("%Y%m%d")
            )

            parameter_data_type = "integer"

        else:
            start_parameter_value = (
                start_value.isoformat()
            )

            end_parameter_value = (
                end_value.isoformat()
            )

            parameter_data_type = "date"


        parameters.extend(
            [
                CompiledParameter(
                    name=start_name,
                    value=start_parameter_value,
                    data_type=parameter_data_type,
                ),
                CompiledParameter(
                    name=end_name,
                    value=end_parameter_value,
                    data_type=parameter_data_type,
                ),
            ]
        )

        expression = (
            f"{reference} >= "
            f"{parameter_placeholder(start_name, dialect)} "
            f"AND {reference} < "
            f"{parameter_placeholder(end_name, dialect)}"
        )

        return (
            expression,
            parameters,
            parameter_index,
        )

    # --------------------------------------------------
    # IN
    # --------------------------------------------------

    if operator == "in":
        values = (
            planned_filter.value
            if isinstance(
                planned_filter.value,
                list,
            )
            else []
        )

        if not values:
            raise ValueError(
                "IN filter requires values."
            )

        placeholders = []

        for value in values:
            parameter_name = (
                f"p{parameter_index}"
            )

            parameter_index += 1

            placeholders.append(
                parameter_placeholder(
                    parameter_name,
                    dialect,
                )
            )

            parameters.append(
                CompiledParameter(
                    name=parameter_name,
                    value=value,
                    data_type=type(
                        value
                    ).__name__,
                )
            )

        return (
            (
                f"{reference} IN "
                f"({', '.join(placeholders)})"
            ),
            parameters,
            parameter_index,
        )

    # --------------------------------------------------
    # BETWEEN OR BETWEEN
    #
    # Example value:
    #
    # 1001,1099|6501,6600
    #
    # Produces:
    #
    # (
    #   CATEGORY BETWEEN :p1 AND :p2
    #   OR
    #   CATEGORY BETWEEN :p3 AND :p4
    # )
    # --------------------------------------------------

    if operator == "between_or_between":
            raw_value = str(
                planned_filter.value
                or ""
            )

            column_data_type = (
                column.data_type
                or ""
            ).strip().upper()

            numeric_types = (
                "NUMBER",
                "INTEGER",
                "INT",
                "DECIMAL",
                "NUMERIC",
                "FLOAT",
                "DOUBLE",
            )

            text_types = (
                "VARCHAR",
                "VARCHAR2",
                "CHAR",
                "NCHAR",
                "NVARCHAR",
                "NVARCHAR2",
                "TEXT",
                "CLOB",
            )

            is_numeric_column = any(
                numeric_type in column_data_type
                for numeric_type in numeric_types
            )

            is_text_column = any(
                text_type in column_data_type
                for text_type in text_types
            )

            ranges = []

            for part in raw_value.split("|"):
                bounds = [
                    item.strip()
                    for item in part.split(",")
                ]

                if len(bounds) != 2:
                    raise ValueError(
                        "between_or_between requires "
                        "ranges in the form "
                        "'start,end|start,end'."
                    )

                if is_numeric_column:
                    try:
                        start_value = int(
                            bounds[0]
                        )
                        end_value = int(
                            bounds[1]
                        )

                    except ValueError as error:
                        raise ValueError(
                            "between_or_between values "
                            "must be numeric for "
                            "numeric columns."
                        ) from error

                    parameter_data_type = "int"

                elif is_text_column:
                    start_value = bounds[0]
                    end_value = bounds[1]
                    parameter_data_type = "string"

                else:
                    # Safe generic fallback:
                    # preserve source values as strings rather
                    # than forcing an implicit numeric conversion.
                    start_value = bounds[0]
                    end_value = bounds[1]
                    parameter_data_type = "string"

                ranges.append(
                    (
                        start_value,
                        end_value,
                        parameter_data_type,
                    )
                )

            if len(ranges) != 2:
                raise ValueError(
                    "between_or_between requires "
                    "exactly two ranges."
                )

            expressions = []

            def governed_literal(
                value,
                parameter_data_type,
            ):
                if parameter_data_type == "int":
                    return str(int(value))

                escaped_value = str(
                    value
                ).replace(
                    "'",
                    "''",
                )

                return (
                    "'"
                    + escaped_value
                    + "'"
                )

            for (
                start_value,
                end_value,
                parameter_data_type,
            ) in ranges:
                start_literal = governed_literal(
                    start_value,
                    parameter_data_type,
                )

                end_literal = governed_literal(
                    end_value,
                    parameter_data_type,
                )

                expressions.append(
                    (
                        f"{reference} BETWEEN "
                        f"{start_literal} "
                        f"AND "
                        f"{end_literal}"
                    )
                )

            return (
                "("
                + " OR ".join(expressions)
                + ")",
                parameters,
                parameter_index,
            )

    # --------------------------------------------------
    # Normal comparison operators
    # =
    # !=
    # >
    # <
    # >=
    # <=
    # contains
    # --------------------------------------------------

    parameter_name = (
        f"p{parameter_index}"
    )

    parameter_index += 1

    value = (
        planned_filter.value
    )

    if operator == "contains":
        value = (
            f"%{value}%"
        )
        sql_operator = "LIKE"
    else:
        sql_operator = operator

    parameters.append(
        CompiledParameter(
            name=parameter_name,
            value=value,
            data_type=type(
                value
            ).__name__,
        )
    )

    expression = (
        f"{reference} "
        f"{sql_operator} "
        f"{parameter_placeholder(parameter_name, dialect)}"
    )

    return (
        expression,
        parameters,
        parameter_index,
    )


def compile_aggregation(
    aggregation: PlannedAggregation,
    table_aliases: dict[int, str],
    dialect: str,
) -> str:
    function_map = {
        "count": "COUNT",
        "sum": "SUM",
        "average": "AVG",
        "minimum": "MIN",
        "maximum": "MAX",
    }

    sql_function = function_map[
        aggregation.function
    ]

    alias = quote_output_alias(
    aggregation.alias,
    dialect,
    )

    if aggregation.function == "count":
        return (
            f"COUNT(*) AS {alias}"
        )

    if (
        aggregation.table is None
        or aggregation.resolved_column
        is None
    ):
        raise ValueError(
            "Aggregation column is missing."
        )

    table = aggregation.table.table

    table_alias = table_aliases[
        table.id
    ]

    column_name = (
        aggregation
        .resolved_column
        .column
        .column_name
    )

    reference = column_reference(
        table_alias,
        column_name,
        dialect,
    )

    return (
        f"{sql_function}({reference}) "
        f"AS {alias}"
    )


def compile_limit(
    sql: str,
    limit: int,
    dialect: str,
) -> str:
    if dialect in {
        "mysql",
        "postgresql",
    }:
        return f"{sql}\nLIMIT {limit}"

    if dialect == "oracle":
        return (
            f"{sql}\nFETCH FIRST "
            f"{limit} ROWS ONLY"
        )

    if dialect == "mssql":
        select_prefix = (
            "SELECT "
        )

        if sql.startswith(
            select_prefix
        ):
            return sql.replace(
                select_prefix,
                (
                    f"SELECT TOP "
                    f"({limit}) "
                ),
                1,
            )

    return sql


def compile_governed_plan(
    database: Session,
    plan: GovernedPlan,
) -> CompiledSQL:
    compiled = CompiledSQL(
        prompt=plan.prompt,
        decision=plan.decision,
        is_compiled=False,
        approved_limit=(
            plan.approved_limit
        ),
        overall_confidence=(
            plan.overall_confidence
        ),
        warnings=list(
            dict.fromkeys(
                plan.warnings
            )
        ),
        errors=list(
            dict.fromkeys(
                plan.blocked_reasons
            )
        ),
        explanation=list(
            plan.explanation
        ),
    )

    if (
        plan.decision != "approved"
        or not plan.is_allowed
    ):
        compiled.errors.append(
            "Only approved governed plans can be compiled."
        )

        return compiled

    physical_tables = (
        plan.reasoning_result[
            "physical_tables"
        ]
    )

    if not physical_tables:
        compiled.errors.append(
            "No physical tables were selected."
        )

        return compiled
    required_table_ids: set[int] = set()

    # Selected result columns
    for item in plan.selected_columns:
        required_table_ids.add(
            item.table.table.id
        )

    # Filters
    for item in plan.filters:
        required_table_ids.add(
            item.table.table.id
        )

    # Grouping
    for item in plan.group_by:
        required_table_ids.add(
            item.table.table.id
        )

    # Ordering
    for item in plan.order_by:
        required_table_ids.add(
            item.table.table.id
        )

    # Aggregation
        # --------------------------------------------------
    # Aggregations
    #
    # Support both:
    #
    # legacy single aggregation
    # plan.aggregation
    #
    # and new multi-measure reports
    # plan.aggregations
    # --------------------------------------------------

    effective_aggregations = (
        plan.aggregations
        if plan.aggregations
        else (
            [plan.aggregation]
            if plan.aggregation
            else []
        )
    )

    for aggregation in effective_aggregations:
        if aggregation.table:
            required_table_ids.add(
                aggregation.table.table.id
            )

    # Approved physical joins
    for mapping in (
        plan.join_mappings.values()
    ):
        required_table_ids.add(
            mapping.source_metadata_table_id
        )

        required_table_ids.add(
            mapping.target_metadata_table_id
        )

    # If nothing explicitly selected, fall back to the
    # strongest physical mapping only.
    if not required_table_ids:
        required_table_ids.add(
            physical_tables[0].table.id
        )

    physical_tables = [
        item
        for item in physical_tables
        if item.table.id
        in required_table_ids
    ]

    data_source_ids = {
        item.table.data_source_id
        for item in physical_tables
    }

    # Include data sources used by bridge tables.
    for mapping in (
        plan.join_mappings.values()
    ):
        if mapping.source_table is not None:
            data_source_ids.add(
                mapping
                .source_table
                .data_source_id
            )

        if mapping.target_table is not None:
            data_source_ids.add(
                mapping
                .target_table
                .data_source_id
            )

    if len(data_source_ids) != 1:
        compiled.errors.append(
            "A single SQL statement cannot use multiple data sources."
        )

        return compiled

    data_source_id = next(
        iter(data_source_ids)
    )

    data_source = database.get(
        DataSource,
        data_source_id,
    )

    if data_source is None:
        compiled.errors.append(
            "The selected data source was not found."
        )

        return compiled

    dialect = normalize_database_type(
        data_source.database_type
    )

    if dialect is None:
        compiled.errors.append(
            (
                "Unsupported database type: "
                f"{data_source.database_type}."
            )
        )

        return compiled

    compiled.dialect = dialect

    unique_tables = {}

    # --------------------------------------------------
    # Tables directly resolved by semantic reasoning
    # --------------------------------------------------

    for item in physical_tables:
        unique_tables[
            item.table.id
        ] = item.table

    # --------------------------------------------------
    # Include bridge tables required by approved joins.
    #
    # Example:
    #
    # FBNK_ACCOUNT
    #      ↓
    # F_COMPANY
    #      ↓
    # F_EB_DISTRICT
    #
    # F_COMPANY may not be directly resolved from the
    # prompt, but it is required to connect the two
    # business entities.
    # --------------------------------------------------

    for mapping in (
        plan.join_mappings.values()
    ):
        source_table = (
            mapping.source_table
        )

        target_table = (
            mapping.target_table
        )

        if source_table is not None:
            unique_tables[
                source_table.id
            ] = source_table

        if target_table is not None:
            unique_tables[
                target_table.id
            ] = target_table

    table_aliases: dict[
        int,
        str
    ] = {}

    for index, table in enumerate(
        unique_tables.values(),
        start=1,
    ):
        alias = f"t{index}"

        table_aliases[
            table.id
        ] = alias

        compiled.tables.append(
            CompiledTable(
                metadata_table_id=(
                    table.id
                ),
                data_source_id=(
                    table.data_source_id
                ),
                schema_name=(
                    table.schema_name
                ),
                table_name=(
                    table.table_name
                ),
                alias=alias,
            )
        )

    selected_expressions = []

    for grouping in plan.group_by:
        table = grouping.table.table

        alias = table_aliases[
            table.id
        ]

        column = (
            grouping
            .resolved_column
            .column
        )

        expression = time_grain_expression(
            alias=alias,
            column=column,
            dialect=dialect,
            time_grain=getattr(
                grouping,
                "time_grain",
                None,
            ),
        )

        result_alias = (
            column.business_name
            or column.column_name
        )

        selected_expressions.append(
            (
                f"{expression} AS "
                f"{quote_output_alias(result_alias, dialect)}"
            )
        )

        effective_aggregations = (
        plan.aggregations
        if plan.aggregations
        else (
            [plan.aggregation]
            if plan.aggregation
            else []
        )
    )

    if effective_aggregations:
        for aggregation in effective_aggregations:
            selected_expressions.append(
                compile_aggregation(
                    aggregation=(
                        aggregation
                    ),
                    table_aliases=(
                        table_aliases
                    ),
                    dialect=dialect,
                )
            )

    else:
        for item in plan.selected_columns:
            table = item.table.table

            alias = table_aliases[
                table.id
            ]

            column = (
                item.resolved_column
                .column
            )

            reference = column_reference(
                alias,
                column.column_name,
                dialect,
            )
            
            # --------------------------------------------------
            # Time-grained grouping ordering
            #
            # If ORDER BY targets the same physical column used
            # by a time-grained GROUP BY, order by the exact same
            # compiled time expression.
            #
            # Example:
            #
            # GROUP BY FLOOR(OPENINGDATE / 100)
            # ORDER BY FLOOR(OPENINGDATE / 100)
            # --------------------------------------------------

            time_grouping = next(
                (
                    grouping
                    for grouping in plan.group_by
                    if (
                        grouping.table.table.id
                        == table.id
                        and grouping
                        .resolved_column
                        .column
                        .id
                        == column.id
                        and getattr(
                            grouping,
                            "time_grain",
                            None,
                        )
                        is not None
                    )
                ),
                None,
            )

            if time_grouping is not None:
                reference = time_grain_expression(
                    alias=alias,
                    column=column,
                    dialect=dialect,
                    time_grain=getattr(
                        time_grouping,
                        "time_grain",
                        None,
                    ),
                )

            output_name = (
                column.business_name
                or column.column_name
            )

            selected_expressions.append(
                (
                    f"{reference} AS "
                    f"{quote_output_alias(output_name, dialect)}"
                )
            )

    if not selected_expressions:
        compiled.errors.append(
            "No approved output columns were selected."
        )

        return compiled

    base_table = physical_tables[
        0
    ].table

    base_alias = table_aliases[
        base_table.id
    ]

    from_clause = (
    f"{qualified_table_name(base_table.schema_name, base_table.table_name, dialect)} "
    f"{table_alias_clause(base_alias, dialect)}"
    )

    joined_table_ids = {
        base_table.id
    }

    join_clauses = []

    # --------------------------------------------------
    # Multi-hop physical join tree
    # --------------------------------------------------

    pending_mappings = list(
        plan.join_mappings.items()
    )

    while pending_mappings:
        progress_made = False
        remaining_mappings = []

        for (
            relationship_id,
            mapping,
        ) in pending_mappings:

            source_table_id = (
                mapping
                .source_metadata_table_id
            )

            target_table_id = (
                mapping
                .target_metadata_table_id
            )

            # Both tables must exist in the
            # selected physical table set.
            if (
                source_table_id
                not in table_aliases
                or target_table_id
                not in table_aliases
            ):
                continue

            source_alias = (
                table_aliases[
                    source_table_id
                ]
            )

            target_alias = (
                table_aliases[
                    target_table_id
                ]
            )

            source_joined = (
                source_table_id
                in joined_table_ids
            )

            target_joined = (
                target_table_id
                in joined_table_ids
            )

            # Source is already connected.
            if (
                source_joined
                and not target_joined
            ):
                join_table = (
                    mapping.target_table
                )

                join_alias = (
                    target_alias
                )

            # Target is already connected.
            elif (
                target_joined
                and not source_joined
            ):
                join_table = (
                    mapping.source_table
                )

                join_alias = (
                    source_alias
                )

            # Neither side is connected yet.
            elif (
                not source_joined
                and not target_joined
            ):
                remaining_mappings.append(
                    (
                        relationship_id,
                        mapping,
                    )
                )

                continue

            # Both sides are already connected.
            else:
                continue

            source_reference = (
                column_reference(
                    source_alias,
                    mapping
                    .source_column
                    .column_name,
                    dialect,
                )
            )

            target_reference = (
                column_reference(
                    target_alias,
                    mapping
                    .target_column
                    .column_name,
                    dialect,
                )
            )

            expression = (
                f"{source_reference} = "
                f"{target_reference}"
            )

            join_type_map = {
                "inner": "INNER JOIN",
                "left": "LEFT JOIN",
                "right": "RIGHT JOIN",
                "full": "FULL OUTER JOIN",
            }

            join_keyword = (
                join_type_map[
                    mapping.join_type
                ]
            )

            join_table_name = (
                qualified_table_name(
                    join_table.schema_name,
                    join_table.table_name,
                    dialect,
                )
            )

            join_table_alias = (
                table_alias_clause(
                    join_alias,
                    dialect,
                )
            )

            join_clause = (
                f"{join_keyword} "
                f"{join_table_name} "
                f"{join_table_alias} "
                f"ON {expression}"
            )

            join_clauses.append(
                join_clause
            )

            joined_table_ids.add(
                join_table.id
            )

            compiled.joins.append(
                CompiledJoin(
                    join_mapping_id=(
                        mapping.id
                    ),
                    relationship_id=(
                        relationship_id
                    ),
                    join_type=(
                        mapping.join_type
                    ),
                    source_table_alias=(
                        source_alias
                    ),
                    source_column_name=(
                        mapping
                        .source_column
                        .column_name
                    ),
                    target_table_alias=(
                        target_alias
                    ),
                    target_column_name=(
                        mapping
                        .target_column
                        .column_name
                    ),
                    expression=expression,
                )
            )

            progress_made = True

        # Nothing else could be connected.
        if not progress_made:
            break

        pending_mappings = (
            remaining_mappings
        )

    unresolved_table_ids = (
        set(
            table_aliases.keys()
        )
        - joined_table_ids
    )

    if unresolved_table_ids:
        compiled.errors.append(
            (
                "The compiler could not construct "
                "a connected physical join tree "
                "for every selected table."
            )
        )

        return compiled

    where_clauses = []
    having_clauses = []
    parameter_index = 1

    # --------------------------------------------------
    # Snapshot-period selection
    #
    # Snapshot measures represent state at a point in
    # time. For grouped historical analysis, select the
    # latest available snapshot once per requested period
    # and join the fact rows to those snapshot dates.
    #
    # This avoids a correlated MAX() subquery against
    # every fact row.
    #
    # Driven entirely by measure metadata.
    # --------------------------------------------------

    snapshot_period_cte = None
    snapshot_period_join = None
    snapshot_period_context = None
    snapshot_time_parameters = None

    snapshot_candidates = []

    if plan.aggregation is not None:
        snapshot_candidates.append(
            plan.aggregation
        )

    for aggregation in getattr(
        plan,
        "aggregations",
        [],
    ) or []:
        if aggregation not in snapshot_candidates:
            snapshot_candidates.append(
                aggregation
            )

    effective_snapshot_aggregation = next(
        (
            aggregation
            for aggregation in snapshot_candidates
            if (
                getattr(
                    aggregation,
                    "temporal_behavior",
                    None,
                )
                == "snapshot"
                and getattr(
                    aggregation,
                    "period_selection",
                    None,
                )
                == "latest_snapshot"
                and getattr(
                    aggregation,
                    "time_axis_table",
                    None,
                )
                is not None
                and getattr(
                    aggregation,
                    "time_axis_column",
                    None,
                )
                is not None
            )
        ),
        None,
    )

    if effective_snapshot_aggregation is not None:
        snapshot_table = (
            effective_snapshot_aggregation
            .time_axis_table
            .table
        )

        snapshot_column = (
            effective_snapshot_aggregation
            .time_axis_column
            .column
        )

        snapshot_alias = table_aliases[
            snapshot_table.id
        ]

        snapshot_reference = (
            column_reference(
                snapshot_alias,
                snapshot_column.column_name,
                dialect,
            )
        )

        snapshot_grouping = next(
            (
                grouping
                for grouping in plan.group_by
                if (
                    grouping.table.table.id
                    == snapshot_table.id
                    and getattr(
                        grouping,
                        "time_grain",
                        None,
                    )
                    is not None
                )
            ),
            None,
        )

        if snapshot_grouping is not None:
            cte_alias = "snapshot_period"
            cte_source_alias = "snapshot_src"

            cte_snapshot_reference = (
                column_reference(
                    cte_source_alias,
                    snapshot_column.column_name,
                    dialect,
                )
            )

            cte_period_expression = (
                time_grain_expression(
                    alias=cte_source_alias,
                    column=snapshot_column,
                    dialect=dialect,
                    time_grain=(
                        snapshot_grouping.time_grain
                    ),
                )
            )

            historical_table_name = (
                qualified_table_name(
                    snapshot_table.schema_name,
                    snapshot_table.table_name,
                    dialect,
                )
            )

            snapshot_period_context = {
                "table": snapshot_table,
                "column": snapshot_column,
                "cte_alias": cte_alias,
                "cte_source_alias": cte_source_alias,
                "snapshot_reference": snapshot_reference,
                "cte_snapshot_reference": cte_snapshot_reference,
                "cte_period_expression": cte_period_expression,
                "historical_table_name": historical_table_name,
                "time_grain": snapshot_grouping.time_grain,
            }

    for planned_filter in (
        plan.filters
    ):
        try:
            (
                expression,
                parameters,
                parameter_index,
            ) = compile_filter(
                planned_filter=(
                    planned_filter
                ),
                table_aliases=(
                    table_aliases
                ),
                dialect=dialect,
                parameter_index=(
                    parameter_index
                ),
            )
        except ValueError as error:
            compiled.errors.append(
                str(error)
            )

            return compiled

        is_snapshot_time_range = False

        # Capture the governed snapshot time-axis range.
        # For snapshot sources that are UNION ALL views,
        # use trusted compiler-derived literals for this
        # physical pruning predicate so Oracle can prune
        # branches efficiently. User/business predicates
        # remain parameterized.
        if snapshot_period_context is not None:
            filter_table = (
                planned_filter.table.table
            )

            filter_column = (
                planned_filter
                .resolved_column
                .column
            )

            if (
                filter_table.id
                == snapshot_period_context["table"].id
                and filter_column.id
                == snapshot_period_context["column"].id
                and len(parameters) >= 2
            ):
                snapshot_time_parameters = list(
                    parameters
                )

                def _trusted_bound_literal(
                    parameter,
                ):
                    value = getattr(
                        parameter,
                        "value",
                        None,
                    )

                    data_type = str(
                        getattr(
                            parameter,
                            "data_type",
                            "",
                        )
                        or ""
                    ).strip().lower()

                    numeric_types = {
                        "int",
                        "integer",
                        "number",
                        "numeric",
                        "decimal",
                        "float",
                        "double",
                    }

                    if data_type in numeric_types:
                        return str(int(value))

                    if isinstance(
                        value,
                        datetime,
                    ):
                        iso_value = (
                            value.date()
                            .isoformat()
                        )
                    elif isinstance(
                        value,
                        date,
                    ):
                        iso_value = (
                            value.isoformat()
                        )
                    else:
                        raw = str(value).strip()

                        if (
                            raw.isdigit()
                            and len(raw) == 8
                        ):
                            return raw

                        iso_value = raw

                    if dialect in {
                        "oracle",
                        "postgresql",
                    }:
                        return (
                            "DATE '"
                            + iso_value
                            + "'"
                        )

                    if dialect == "mssql":
                        return (
                            "CAST('"
                            + iso_value
                            + "' AS DATE)"
                        )

                    return (
                        "'"
                        + iso_value.replace(
                            "'",
                            "''",
                        )
                        + "'"
                    )

                for parameter in parameters:
                    expression = expression.replace(
                        ":" + parameter.name,
                        _trusted_bound_literal(
                            parameter
                        ),
                    )

                is_snapshot_time_range = True

        where_clauses.append(
            expression
        )

        if not is_snapshot_time_range:
            compiled.parameters.extend(
                parameters
            )

    # --------------------------------------------------
    # Build bounded latest-snapshot lookups.
    #
    # Instead of scanning the full historical source and
    # GROUP BY-ing every daily snapshot row, split the
    # governed date range into requested periods and issue
    # one bounded MAX(time_axis) lookup per period.
    #
    # This is generic and metadata-driven:
    #   temporal_behavior = snapshot
    #   period_selection   = latest_snapshot
    #   time_grain         = day/week/month/quarter/year
    # --------------------------------------------------

    if snapshot_period_context is not None:
        context = snapshot_period_context

        if (
            snapshot_time_parameters is not None
            and len(snapshot_time_parameters) >= 2
        ):
            from datetime import (
                date as _date,
                datetime as _datetime,
                timedelta as _timedelta,
            )

            def _to_date(value):
                if isinstance(value, _datetime):
                    return value.date()

                if isinstance(value, _date):
                    return value

                if isinstance(value, (int, float)):
                    raw = str(int(value))
                else:
                    raw = str(value).strip()

                for fmt in (
                    "%Y%m%d",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                ):
                    try:
                        return _datetime.strptime(
                            raw,
                            fmt,
                        ).date()
                    except ValueError:
                        pass

                return None

            def _from_date(value, template):
                if isinstance(template, _datetime):
                    return _datetime.combine(
                        value,
                        _datetime.min.time(),
                    )

                if isinstance(template, _date):
                    return value

                if isinstance(template, int):
                    return int(
                        value.strftime("%Y%m%d")
                    )

                if isinstance(template, float):
                    return int(
                        value.strftime("%Y%m%d")
                    )

                raw_template = str(
                    template
                ).strip()

                if (
                    raw_template.isdigit()
                    and len(raw_template) == 8
                ):
                    return value.strftime(
                        "%Y%m%d"
                    )

                if "-" in raw_template:
                    return value.strftime(
                        "%Y-%m-%d"
                    )

                if "/" in raw_template:
                    return value.strftime(
                        "%Y/%m/%d"
                    )

                return value.strftime(
                    "%Y%m%d"
                )

            def _next_period_boundary(
                value,
                grain,
            ):
                normalized_grain = (
                    str(grain or "")
                    .strip()
                    .lower()
                )

                if normalized_grain == "day":
                    return value + _timedelta(
                        days=1
                    )

                if normalized_grain == "week":
                    return value + _timedelta(
                        days=7
                    )

                if normalized_grain == "month":
                    if value.month == 12:
                        return _date(
                            value.year + 1,
                            1,
                            1,
                        )

                    return _date(
                        value.year,
                        value.month + 1,
                        1,
                    )

                if normalized_grain == "quarter":
                    quarter_start_month = (
                        ((value.month - 1) // 3)
                        * 3
                        + 1
                    )

                    next_month = (
                        quarter_start_month
                        + 3
                    )

                    next_year = value.year

                    if next_month > 12:
                        next_month -= 12
                        next_year += 1

                    return _date(
                        next_year,
                        next_month,
                        1,
                    )

                if normalized_grain == "year":
                    return _date(
                        value.year + 1,
                        1,
                        1,
                    )

                return None

            start_parameter = (
                snapshot_time_parameters[0]
            )

            end_parameter = (
                snapshot_time_parameters[1]
            )

            start_value = getattr(
                start_parameter,
                "value",
                None,
            )

            end_value = getattr(
                end_parameter,
                "value",
                None,
            )

            start_date = _to_date(
                start_value
            )

            end_date = _to_date(
                end_value
            )

            period_ranges = []

            if (
                start_date is not None
                and end_date is not None
                and start_date < end_date
            ):
                # Do not generate empty future periods for
                # an open current-year/current-period range.
                today = _date.today()

                effective_end = end_date

                if (
                    start_date <= today
                    and today < end_date
                ):
                    current_period_end = (
                        _next_period_boundary(
                            today,
                            context[
                                "time_grain"
                            ],
                        )
                    )

                    if current_period_end is not None:
                        effective_end = min(
                            end_date,
                            current_period_end,
                        )

                cursor = start_date

                while cursor < effective_end:
                    next_boundary = (
                        _next_period_boundary(
                            cursor,
                            context[
                                "time_grain"
                            ],
                        )
                    )

                    if (
                        next_boundary is None
                        or next_boundary <= cursor
                    ):
                        break

                    period_end = min(
                        next_boundary,
                        effective_end,
                    )

                    period_ranges.append(
                        (
                            cursor,
                            period_end,
                        )
                    )

                    cursor = period_end

            if period_ranges:
                lookup_queries = []

                def _period_literal(
                    value,
                    template_parameter,
                ):
                    data_type = str(
                        getattr(
                            template_parameter,
                            "data_type",
                            "",
                        )
                        or ""
                    ).strip().lower()

                    numeric_types = {
                        "int",
                        "integer",
                        "number",
                        "numeric",
                        "decimal",
                        "float",
                        "double",
                    }

                    if data_type in numeric_types:
                        return str(
                            int(value.strftime("%Y%m%d"))
                        )

                    iso_value = value.strftime(
                        "%Y-%m-%d"
                    )

                    if dialect == "oracle":
                        return (
                            "DATE '"
                            + iso_value
                            + "'"
                        )

                    if dialect == "postgresql":
                        return (
                            "DATE '"
                            + iso_value
                            + "'"
                        )

                    if dialect == "mssql":
                        return (
                            "CAST('"
                            + iso_value
                            + "' AS DATE)"
                        )

                    return (
                        "'"
                        + iso_value
                        + "'"
                    )

                for (
                    period_start,
                    period_end,
                ) in period_ranges:
                    start_literal = (
                        _period_literal(
                            period_start,
                            start_parameter,
                        )
                    )

                    end_literal = (
                        _period_literal(
                            period_end,
                            end_parameter,
                        )
                    )

                    lookup_queries.append(
                        (
                            "    SELECT MAX("
                            + context[
                                "cte_snapshot_reference"
                            ]
                            + ") AS snapshot_date\n"
                            + "    FROM "
                            + context[
                                "historical_table_name"
                            ]
                            + " "
                            + table_alias_clause(
                                context[
                                    "cte_source_alias"
                                ],
                                dialect,
                            )
                            + "\n"
                            + "    WHERE "
                            + context[
                                "cte_snapshot_reference"
                            ]
                            + f" >= {start_literal}"
                            + " AND "
                            + context[
                                "cte_snapshot_reference"
                            ]
                            + f" < {end_literal}"
                        )
                    )

                snapshot_period_cte = (
                    f"{context['cte_alias']} AS (\n"
                    + "\n    UNION ALL\n".join(
                        lookup_queries
                    )
                    + "\n)"
                )

        # Safe semantic fallback when no two-bound governed
        # range was available. This preserves latest-snapshot
        # correctness even though it may be slower.
        if snapshot_period_cte is None:
            snapshot_period_cte = (
                f"{context['cte_alias']} AS (\n"
                f"    SELECT\n"
                f"        MAX("
                f"{context['cte_snapshot_reference']}) "
                f"AS snapshot_date\n"
                f"    FROM "
                f"{context['historical_table_name']} "
                f"{table_alias_clause(context['cte_source_alias'], dialect)}\n"
                f"    GROUP BY "
                f"{context['cte_period_expression']}\n"
                f")"
            )

        snapshot_period_join = (
            f"INNER JOIN "
            f"{context['cte_alias']} "
            f"ON {context['snapshot_reference']} = "
            f"{context['cte_alias']}.snapshot_date"
        )

    group_by_expressions = []

    for grouping in plan.group_by:
        table = grouping.table.table

        alias = table_aliases[
            table.id
        ]

        column = (
            grouping
            .resolved_column
            .column
        )

        group_by_expressions.append(
            time_grain_expression(
                alias=alias,
                column=column,
                dialect=dialect,
                time_grain=getattr(
                    grouping,
                    "time_grain",
                    None,
                ),
            )
        )

    order_by_expressions = []

    for ordering in plan.order_by:
        table = ordering.table.table

        alias = table_aliases[
            table.id
        ]

        column = (
            ordering
            .resolved_column
            .column
        )

        reference = column_reference(
            alias,
            column.column_name,
            dialect,
        )
        
        # If ORDER BY targets the same physical column
        # used by a time-grained GROUP BY, order by
        # the exact same grouped expression.
        time_grouping = next(
            (
                grouping
                for grouping in plan.group_by
                if (
                    grouping.table.table.id
                    == table.id
                    and grouping
                    .resolved_column
                    .column
                    .id
                    == column.id
                    and getattr(
                        grouping,
                        "time_grain",
                        None,
                    )
                    is not None
                )
            ),
            None,
        )

        if time_grouping is not None:
            reference = time_grain_expression(
                alias=alias,
                column=column,
                dialect=dialect,
                time_grain=getattr(
                    time_grouping,
                    "time_grain",
                    None,
                ),
            )

        # If ORDER BY targets the same physical column
        # used by the aggregation, order by the aggregate
        # expression instead of the raw column.
        if (
            plan.aggregation
            and plan.aggregation.table
            and plan.aggregation.resolved_column
            and (
                plan.aggregation.table.table.id
                == table.id
            )
            and (
                plan.aggregation
                .resolved_column
                .column
                .id
                == column.id
            )
            and plan.aggregation.function
            != "count"
        ):
            function_map = {
                "sum": "SUM",
                "average": "AVG",
                "minimum": "MIN",
                "maximum": "MAX",
            }

            sql_function = function_map.get(
                plan.aggregation.function
            )

            if sql_function:
                reference = (
                    f"{sql_function}"
                    f"({reference})"
                )

        direction = (
            "DESC"
            if ordering.direction
            == "desc"
            else "ASC"
        )

        # Oracle places NULL values first for DESC.
        # For business rankings, NULL values should
        # always appear after valid numeric results.
        null_ordering = ""

        if dialect == "oracle":
            null_ordering = " NULLS LAST"

        order_by_expressions.append(
            f"{reference} "
            f"{direction}"
            f"{null_ordering}"
        )

        # --------------------------------------------------
    # Grouped COUNT ranking
    #
    # COUNT(*) has no resolved physical column, so the
    # normal PlannedSort path cannot create an ORDER BY.
    #
    # Examples:
    #
    # "Show top 10 branches by number of active accounts"
    #     -> ORDER BY COUNT(*) DESC
    #
    # "Show bottom 5 districts by inactive account count"
    #     -> ORDER BY COUNT(*) ASC
    # --------------------------------------------------

    normalized_prompt = (
        plan.normalized_prompt
        or ""
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

    prompt_words = set(
        normalized_prompt.split()
    )

    is_count_ranking = (
        plan.aggregation is not None
        and plan.aggregation.function
        == "count"
        and bool(
            plan.group_by
        )
        and bool(
            prompt_words
            & ranking_words
        )
    )

    if (
        is_count_ranking
        and not order_by_expressions
    ):
        count_direction = "DESC"

        if (
            "bottom" in prompt_words
            or "lowest" in prompt_words
            or "smallest" in prompt_words
            or "least" in prompt_words
        ):
            count_direction = "ASC"

        order_by_expressions.append(
            f"COUNT(*) "
            f"{count_direction}"
        )
        # --------------------------------------------------
    # Canonical ordering for time-series/grouped results
    # --------------------------------------------------

    time_grouping = next(
        (
            grouping
            for grouping in plan.group_by
            if getattr(grouping, "time_grain", None)
            is not None
        ),
        None,
    )

    if time_grouping is not None:
        time_table = time_grouping.table.table
        time_column = (
            time_grouping
            .resolved_column
            .column
        )

        time_alias = table_aliases[
            time_table.id
        ]

        time_order_expression = (
            time_grain_expression(
                alias=time_alias,
                column=time_column,
                dialect=dialect,
                time_grain=(
                    time_grouping.time_grain
                ),
            )
        )

        order_by_expressions = [
            (
                f"{time_order_expression} ASC"
                + (
                    " NULLS LAST"
                    if dialect == "oracle"
                    else ""
                )
            )
        ]
    sql_parts = []

    if snapshot_period_cte:
        sql_parts.extend(
            [
                "WITH",
                f"    {snapshot_period_cte}",
            ]
        )

    sql_parts.extend(
        [
            "SELECT",
            "    "
            + ",\n    ".join(
                selected_expressions
            ),
            "FROM",
            f"    {from_clause}",
        ]
    )

    for join_clause in join_clauses:
        sql_parts.append(
            f"    {join_clause}"
        )

    if snapshot_period_join:
        sql_parts.append(
            f"    {snapshot_period_join}"
        )

    if where_clauses:
        sql_parts.extend(
            [
                "WHERE",
                "    "
                + "\n    AND ".join(
                    where_clauses
                ),
            ]
        )

    if group_by_expressions:
        sql_parts.extend(
            [
                "GROUP BY",
                "    "
                + ",\n    ".join(
                    group_by_expressions
                ),
            ]
        )

    if having_clauses:
        sql_parts.extend(
            [
                "HAVING",
                "    "
                + "\n    AND ".join(
                    having_clauses
                ),
            ]
    )

        if (
        plan.aggregation is not None
        and plan.aggregation.resolved_column is not None
        and plan.intent == "ranking"
    ):
            aggregation_table = (
                plan.aggregation.table.table
            )

        aggregation_alias = (
            table_aliases[
                aggregation_table.id
            ]
        )

        aggregation_column = (
            plan.aggregation
            .resolved_column
            .column
        )

        aggregation_reference = (
            column_reference(
                aggregation_alias,
                aggregation_column.column_name,
                dialect,
            )
        )

        function_map = {
            "sum": "SUM",
            "average": "AVG",
            "minimum": "MIN",
            "maximum": "MAX",
        }

        sql_function = (
            function_map.get(
                plan.aggregation.function
            )
        )

        if sql_function:
            having_clauses.append(
                f"{sql_function}"
                f"({aggregation_reference}) "
                f"IS NOT NULL"
            )

    if order_by_expressions:
        sql_parts.extend(
            [
                "ORDER BY",
                "    "
                + ",\n    ".join(
                    order_by_expressions
                ),
            ]
        )
        
    

    sql = "\n".join(
        sql_parts
    )

    

    sql = compile_limit(
        sql=sql,
        limit=plan.approved_limit,
        dialect=dialect,
    )

    compiled.sql = sql
    
    print("\n=== COMPILED SQL DEBUG ===")
    print(compiled.sql)
    print("PARAMETERS:")
    print(compiled.parameters)
    print("ERRORS:")
    print(compiled.errors)
    print("=== END COMPILED SQL DEBUG ===\n")

    compiled.is_compiled = True

    compiled.explanation.append(
        (
            f"Compiled a read-only "
            f"{dialect} SELECT statement."
        )
    )

    compiled.explanation.append(
        (
            f"The statement uses "
            f"{len(compiled.tables)} table(s), "
            f"{len(compiled.joins)} join(s), "
            f"and {len(compiled.parameters)} "
            f"bound parameter(s)."
        )
    )

    return compiled


def create_and_compile_sql(
    database: Session,
    prompt: str,
    domain_id: int | None,
    requested_limit: int,
    maximum_entities: int,
    maximum_path_depth: int,
    user_role: str,
    branch_scope_value: str | None = None,
    allow_confidential_aggregate: bool = False,
) -> CompiledSQL:
    plan = create_governed_query_plan(
        database=database,
        prompt=prompt,
        domain_id=domain_id,
        requested_limit=requested_limit,
        maximum_entities=maximum_entities,
        maximum_path_depth=maximum_path_depth,
        user_role=user_role,
        branch_scope_value=branch_scope_value,
        allow_confidential_aggregate=(
            allow_confidential_aggregate
        ),
    )

    return compile_governed_plan(
        database=database,
        plan=plan,
    )
