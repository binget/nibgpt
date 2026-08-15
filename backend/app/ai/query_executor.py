from __future__ import annotations

import re
import time
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.sql_compiler import (
    create_and_compile_sql,
)

from app.models.data_source import (
    DataSource,
)

from app.services.external_database import (
    create_external_engine,
)

from app.ai.answer_generator import (
    generate_answer,
)


READ_ONLY_FORBIDDEN_WORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace",
    "merge",
    "grant",
    "revoke",
    "call",
    "execute",
    "exec",
}


def object_value(
    obj,
    name: str,
    default=None,
):
    if isinstance(
        obj,
        dict,
    ):
        return obj.get(
            name,
            default,
        )

    return getattr(
        obj,
        name,
        default,
    )


def validate_read_only_sql(
    sql: str,
) -> None:
    if not sql:
        raise ValueError(
            "Compiled SQL is empty."
        )

    cleaned = sql.strip()

    # Compiler-generated reports should currently
    # always be SELECT statements.
    if not re.match(
        r"^SELECT\b",
        cleaned,
        flags=re.IGNORECASE,
    ):
        raise ValueError(
            "Only SELECT statements may be executed."
        )

    # Do not allow multiple statements.
    without_trailing_semicolon = (
        cleaned.rstrip(";").strip()
    )

    if ";" in without_trailing_semicolon:
        raise ValueError(
            "Multiple SQL statements are not allowed."
        )

    # Remove quoted string values before performing
    # the secondary keyword safety scan.
    keyword_scan = re.sub(
        r"'(?:''|[^'])*'",
        "''",
        without_trailing_semicolon,
    )

    words = set(
        re.findall(
            r"\b[a-zA-Z_]+\b",
            keyword_scan.lower(),
        )
    )

    forbidden = (
        words
        & READ_ONLY_FORBIDDEN_WORDS
    )

    if forbidden:
        raise ValueError(
            "Unsafe SQL keyword detected: "
            + ", ".join(
                sorted(forbidden)
            )
        )


def make_json_safe(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return float(value)

    if isinstance(
        value,
        (date, datetime),
    ):
        return value.isoformat()

    if isinstance(
        value,
        bytes,
    ):
        try:
            return value.decode(
                "utf-8"
            )
        except UnicodeDecodeError:
            return value.hex()

    return value


def execute_governed_prompt(
    database: Session,
    prompt: str,
    domain_id: int | None,
    requested_limit: int,
    maximum_entities: int,
    maximum_path_depth: int,
    user_role: str,
) -> dict[str, Any]:

    compilation_result = (
        create_and_compile_sql(
            database=database,
            prompt=prompt,
            domain_id=domain_id,
            requested_limit=(
                requested_limit
            ),
            maximum_entities=(
                maximum_entities
            ),
            maximum_path_depth=(
                maximum_path_depth
            ),
            user_role=user_role,
        )
    )

    compiled = object_value(
        compilation_result,
        "compiled",
        compilation_result,
    )

    decision = object_value(
        compiled,
        "decision",
        "unknown",
    )

    is_compiled = bool(
        object_value(
            compiled,
            "is_compiled",
            False,
        )
    )

    warnings = list(
        object_value(
            compiled,
            "warnings",
            [],
        )
        or []
    )

    errors = list(
        object_value(
            compiled,
            "errors",
            [],
        )
        or []
    )

    explanation = list(
        object_value(
            compiled,
            "explanation",
            [],
        )
        or []
    )

    if (
        decision != "approved"
        or not is_compiled
    ):
        return {
            "success": False,
            "answer": None,
            "prompt": prompt,
            "decision": decision,
            "data_source_id": None,
            "data_source_name": None,
            "sql": object_value(
                compiled,
                "sql",
            ),
            "parameters": {},
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": None,
            "warnings": warnings,
            "errors": errors,
            "explanation": explanation,
        }

    sql = object_value(
        compiled,
        "sql",
    )

    validate_read_only_sql(
        sql
    )

    compiled_tables = list(
        object_value(
            compiled,
            "tables",
            [],
        )
        or []
    )

    if not compiled_tables:
        raise ValueError(
            "Compiled query has no physical data source."
        )

    data_source_ids = {
        object_value(
            table,
            "data_source_id",
        )
        for table in compiled_tables
    }

    data_source_ids.discard(
        None
    )

    if len(data_source_ids) != 1:
        raise ValueError(
            "Query execution currently requires "
            "exactly one physical data source."
        )

    data_source_id = next(
        iter(
            data_source_ids
        )
    )

    source = database.get(
        DataSource,
        data_source_id,
    )

    if source is None:
        raise ValueError(
            "Compiled data source was not found."
        )

    if not source.is_active:
        raise ValueError(
            "The selected data source is disabled."
        )

    parameter_objects = list(
        object_value(
            compiled,
            "parameters",
            [],
        )
        or []
    )

    parameters = {
        object_value(
            item,
            "name",
        ): object_value(
            item,
            "value",
        )
        for item in parameter_objects
    }

    engine = create_external_engine(
        source
    )

    started = (
        time.perf_counter()
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(sql),
                parameters,
            )

            column_names = list(
                result.keys()
            )

            raw_rows = (
                result.fetchall()
            )

            rows = []

            for raw_row in raw_rows:
                mapping = (
                    raw_row._mapping
                )

                row = {
                    str(key): make_json_safe(
                        value
                    )
                    for key, value
                    in mapping.items()
                }

                rows.append(
                    row
                )

    finally:
        engine.dispose()

    elapsed_ms = round(
        (
            time.perf_counter()
            - started
        )
        * 1000,
        2,
    )

    safe_parameters = {
    key: make_json_safe(
        value
    )
    for key, value
    in parameters.items()
    }

    answer = generate_answer(
        prompt=prompt,
        columns=column_names,
        rows=rows,
        data_source_name=(
            source.name
        ),
    )

    return {
        "answer": answer,
        "success": True,
        "prompt": prompt,
        "decision": decision,
        "data_source_id": (
            source.id
        ),
        "data_source_name": (
            source.name
        ),
        "sql": sql,
        "parameters": (
            safe_parameters
        ),
        "columns": column_names,
        "rows": rows,
        "row_count": len(
            rows
        ),
        "execution_time_ms": (
            elapsed_ms
        ),
        "warnings": warnings,
        "errors": [],
        "explanation": explanation,
    }