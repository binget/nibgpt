from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.semantic_time_series import (
    SemanticTimeSeries,
)


def build_signature(
    value: Any,
    default: str = "none",
) -> str:
    """
    Build a stable cache signature from dimensions,
    filters, scope information, or other governed
    semantic context.
    """

    if value is None:
        return default

    if value == "":
        return default

    if value == {}:
        return default

    if value == []:
        return default

    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def get_cached_series(
    database: Session,
    business_measure_id: int,
    period_grain: str,
    dimension_signature: str = "none",
    filter_signature: str = "none",
    scope_signature: str = "enterprise",
) -> list[SemanticTimeSeries]:

    return (
        database.query(
            SemanticTimeSeries
        )
        .filter(
            SemanticTimeSeries.business_measure_id
            == business_measure_id,
            SemanticTimeSeries.period_grain
            == period_grain,
            SemanticTimeSeries.dimension_signature
            == dimension_signature,
            SemanticTimeSeries.filter_signature
            == filter_signature,
            SemanticTimeSeries.scope_signature
            == scope_signature,
        )
        .order_by(
            SemanticTimeSeries.period_key.asc()
        )
        .all()
    )


def upsert_series_point(
    database: Session,
    business_measure_id: int,
    period_grain: str,
    period_key: str,
    value: Decimal | float | int | str,
    dimension_signature: str = "none",
    filter_signature: str = "none",
    scope_signature: str = "enterprise",
    source_data_source_id: int | None = None,
    source_table: str | None = None,
) -> SemanticTimeSeries:

    existing = (
        database.query(
            SemanticTimeSeries
        )
        .filter(
            SemanticTimeSeries.business_measure_id
            == business_measure_id,
            SemanticTimeSeries.period_grain
            == period_grain,
            SemanticTimeSeries.period_key
            == str(period_key),
            SemanticTimeSeries.dimension_signature
            == dimension_signature,
            SemanticTimeSeries.filter_signature
            == filter_signature,
            SemanticTimeSeries.scope_signature
            == scope_signature,
        )
        .one_or_none()
    )

    decimal_value = Decimal(
        str(value).replace(",", "")
    )

    if existing is not None:
        existing.value = decimal_value
        existing.source_data_source_id = (
            source_data_source_id
        )
        existing.source_table = source_table
        existing.calculated_at = datetime.utcnow()

        return existing

    point = SemanticTimeSeries(
        business_measure_id=business_measure_id,
        period_grain=period_grain,
        period_key=str(period_key),
        value=decimal_value,
        dimension_signature=dimension_signature,
        filter_signature=filter_signature,
        scope_signature=scope_signature,
        source_data_source_id=source_data_source_id,
        source_table=source_table,
        calculated_at=datetime.utcnow(),
    )

    database.add(
        point
    )

    return point


def upsert_series(
    database: Session,
    business_measure_id: int,
    period_grain: str,
    rows: list[dict[str, Any]],
    period_column: str,
    value_column: str,
    dimension_signature: str = "none",
    filter_signature: str = "none",
    scope_signature: str = "enterprise",
    source_data_source_id: int | None = None,
    source_table: str | None = None,
    commit: bool = True,
) -> int:

    saved = 0

    for row in rows:
        period_key = row.get(
            period_column
        )

        value = row.get(
            value_column
        )

        if (
            period_key is None
            or value is None
        ):
            continue

        upsert_series_point(
            database=database,
            business_measure_id=business_measure_id,
            period_grain=period_grain,
            period_key=str(period_key),
            value=value,
            dimension_signature=dimension_signature,
            filter_signature=filter_signature,
            scope_signature=scope_signature,
            source_data_source_id=source_data_source_id,
            source_table=source_table,
        )

        saved += 1

    if commit:
        database.commit()

    return saved


def cached_series_to_rows(
    series: list[SemanticTimeSeries],
    period_column: str = "Period",
    value_column: str = "Value",
) -> list[dict[str, Any]]:

    return [
        {
            period_column: point.period_key,
            value_column: float(point.value),
        }
        for point in series
    ]
    
def get_cached_series_by_signature(
    database: Session,
    period_grain: str,
    filter_signature: str,
    scope_signature: str,
) -> list[SemanticTimeSeries]:
    """
    Fast lookup before touching the external database.

    filter_signature represents the normalized governed
    historical request. scope_signature prevents data from
    leaking across authorized scopes.
    """

    return (
        database.query(
            SemanticTimeSeries
        )
        .filter(
            SemanticTimeSeries.period_grain
            == period_grain,
            SemanticTimeSeries.filter_signature
            == filter_signature,
            SemanticTimeSeries.scope_signature
            == scope_signature,
        )
        .order_by(
            SemanticTimeSeries.period_key.asc()
        )
        .all()
    )


def build_scope_signature(
    governance_role: str,
    branch_scope_value: str | None,
) -> str:
    """
    Enterprise users share enterprise cache.
    Branch-scoped requests receive their own cache key.
    """

    if not branch_scope_value:
        return "enterprise"

    return build_signature(
        {
            "role": governance_role,
            "branch": branch_scope_value,
        }
    )
