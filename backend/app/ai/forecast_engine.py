from __future__ import annotations

import math
import re
import calendar
from datetime import date
from typing import Any



FORECAST_PATTERNS = (
    r"\bforecast\b",
    r"\bpredict\b",
    r"\bprojection\b",
    r"\bproject\b",
)


def is_forecast_request(
    prompt: str,
) -> bool:
    normalized = (
        prompt or ""
    ).lower()

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in FORECAST_PATTERNS
    )


def extract_forecast_horizon(
    prompt: str,
    default: int = 3,
    maximum: int = 24,
) -> int:
    normalized = (
        prompt or ""
    ).lower()

    match = re.search(
        r"\b(?:next|following)\s+(\d+)\s+months?\b",
        normalized,
    )

    if not match:
        match = re.search(
            r"\b(\d+)\s+months?\b",
            normalized,
        )

    if not match:
        return default

    horizon = int(
        match.group(1)
    )

    return max(
        1,
        min(
            horizon,
            maximum,
        ),
    )


def extract_forecast_subject(
    prompt: str,
) -> str:
    subject = (
        prompt or ""
    ).strip()

    subject = re.sub(
        r"^\s*(forecast|predict|project)\s+",
        "",
        subject,
        flags=re.IGNORECASE,
    )

    subject = re.sub(
        r"\bfor\s+(?:the\s+)?next\s+\d+\s+months?\b",
        "",
        subject,
        flags=re.IGNORECASE,
    )

    subject = re.sub(
        r"\b(?:the\s+)?next\s+\d+\s+months?\b",
        "",
        subject,
        flags=re.IGNORECASE,
    )

    subject = re.sub(
        r"\s+",
        " ",
        subject,
    ).strip(" .?")

    return subject


def build_forecast_history_prompt(
    prompt: str,
) -> str:
    subject = extract_forecast_subject(
        prompt
    )

    if not subject:
        raise ValueError(
            "Unable to determine the measure "
            "that should be forecast."
        )

    return (
        f"Show monthly {subject} trend "
        f"this year"
    )


def _parse_period(
    value: Any,
) -> tuple[int, int] | None:
    if value is None:
        return None

    raw = str(
        value
    ).strip()

    # Common semantic compiler output:
    # YYYYMM
    if re.fullmatch(
        r"\d{6}",
        raw,
    ):
        year = int(
            raw[:4]
        )
        month = int(
            raw[4:6]
        )

        if 1 <= month <= 12:
            return (
                year,
                month,
            )

    # Allow YYYY-MM.
    match = re.fullmatch(
        r"(\d{4})-(\d{2})",
        raw,
    )

    if match:
        year = int(
            match.group(1)
        )
        month = int(
            match.group(2)
        )

        if 1 <= month <= 12:
            return (
                year,
                month,
            )

    return None


def _next_month(
    year: int,
    month: int,
) -> tuple[int, int]:
    if month == 12:
        return (
            year + 1,
            1,
        )

    return (
        year,
        month + 1,
    )


def _find_period_column(
    rows: list[dict[str, Any]],
) -> str | None:
    if not rows:
        return None

    keys = list(
        rows[0].keys()
    )

    preferred_tokens = (
        "period",
        "month",
        "date",
        "procdate",
        "opening",
    )

    for key in keys:
        normalized = (
            str(key)
            .lower()
            .replace("_", " ")
        )

        if any(
            token in normalized
            for token in preferred_tokens
        ):
            for row in rows:
                if _parse_period(
                    row.get(key)
                ):
                    return key

    for key in keys:
        for row in rows:
            if _parse_period(
                row.get(key)
            ):
                return key

    return None


def _is_numeric(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(
        value,
        bool,
    ):
        return False

    if isinstance(
        value,
        (int, float),
    ):
        return math.isfinite(
            float(value)
        )

    try:
        numeric = float(
            str(value).replace(
                ",",
                "",
            )
        )

        return math.isfinite(
            numeric
        )

    except (
        TypeError,
        ValueError,
    ):
        return False


def _find_measure_column(
    rows: list[dict[str, Any]],
    period_column: str,
) -> str | None:
    if not rows:
        return None

    for key in rows[0].keys():
        if key == period_column:
            continue

        numeric_values = [
            row.get(key)
            for row in rows
            if row.get(key) is not None
        ]

        if (
            numeric_values
            and all(
                _is_numeric(value)
                for value in numeric_values
            )
        ):
            return key

    return None


def _linear_regression(
    values: list[float],
) -> tuple[
    float,
    float,
    float,
]:
    n = len(
        values
    )

    x_values = list(
        range(n)
    )

    x_mean = sum(
        x_values
    ) / n

    y_mean = sum(
        values
    ) / n

    denominator = sum(
        (
            x - x_mean
        ) ** 2
        for x in x_values
    )

    if denominator == 0:
        slope = 0.0
    else:
        slope = (
            sum(
                (
                    x - x_mean
                )
                * (
                    y - y_mean
                )
                for x, y in zip(
                    x_values,
                    values,
                )
            )
            / denominator
        )

    intercept = (
        y_mean
        - slope
        * x_mean
    )

    predicted = [
        intercept
        + slope * x
        for x in x_values
    ]

    total_variance = sum(
        (
            y - y_mean
        ) ** 2
        for y in values
    )

    residual_variance = sum(
        (
            actual - estimate
        ) ** 2
        for actual, estimate
        in zip(
            values,
            predicted,
        )
    )

    if total_variance == 0:
        r_squared = 1.0
    else:
        r_squared = max(
            0.0,
            min(
                1.0,
                1.0
                - residual_variance
                / total_variance,
            ),
        )

    return (
        slope,
        intercept,
        r_squared,
    )


def _confidence_label(
    r_squared: float,
    sample_size: int,
) -> str:
    if (
        sample_size >= 9
        and r_squared >= 0.70
    ):
        return "high"

    if (
        sample_size >= 6
        and r_squared >= 0.35
    ):
        return "medium"

    return "low"


def _format_value(
    value: float,
) -> str:
    absolute = abs(
        value
    )

    if absolute >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:,.2f} billion"
        )

    if absolute >= 1_000_000:
        return (
            f"{value / 1_000_000:,.2f} million"
        )

    return f"{value:,.2f}"


def forecast_from_reporting_result(
    result: dict[str, Any],
    forecast_prompt: str,
) -> dict[str, Any]:
    if not isinstance(
        result,
        dict,
    ):
        raise ValueError(
            "Historical reporting result is invalid."
        )

    if not result.get(
        "success"
    ):
        return result

    rows = list(
        result.get(
            "rows"
        )
        or []
    )

    if not rows:
        result["success"] = False
        result["errors"] = (
            list(
                result.get(
                    "errors"
                )
                or []
            )
            + [
                "Forecasting requires historical data."
            ]
        )
        return result

    period_column = (
        _find_period_column(
            rows
        )
    )

    if period_column is None:
        result["success"] = False
        result["errors"] = [
            "No monthly period column was found "
            "in the historical result."
        ]
        return result

    measure_column = (
        _find_measure_column(
            rows,
            period_column,
        )
    )

    if measure_column is None:
        result["success"] = False
        result["errors"] = [
            "No numeric measure was found "
            "for forecasting."
        ]
        return result

    points: list[
        tuple[
            int,
            int,
            float,
        ]
    ] = []

    current = date.today()

    for row in rows:
        period = _parse_period(
            row.get(
                period_column
            )
        )

        if period is None:
            continue

        value = row.get(
            measure_column
        )

        if not _is_numeric(
            value
        ):
            continue

        year, month = period

        # Do not train on the current partial month.
        if (
            year == current.year
            and month == current.month
        ):
            continue

        numeric_value = float(
            str(value).replace(
                ",",
                "",
            )
        )

        points.append(
            (
                year,
                month,
                numeric_value,
            )
        )

    points.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    # Keep at most the most recent 12 completed months.
    points = points[
        -12:
    ]

    if len(points) < 4:
        result["success"] = False
        result["errors"] = [
            "At least 4 completed monthly periods "
            "are required for forecasting."
        ]
        return result

    historical_values = [
        point[2]
        for point in points
    ]

    (
        slope,
        intercept,
        r_squared,
    ) = _linear_regression(
        historical_values
    )

    horizon = (
        extract_forecast_horizon(
            forecast_prompt
        )
    )

    last_year = points[-1][0]
    last_month = points[-1][1]

    forecast_rows = []

    year = last_year
    month = last_month

    for step in range(
        1,
        horizon + 1,
    ):
        year, month = (
            _next_month(
                year,
                month,
            )
        )

        x_value = (
            len(
                historical_values
            )
            - 1
            + step
        )

        forecast_value = (
            intercept
            + slope
            * x_value
        )

        # Generic financial/count safety:
        # deterministic trend should not emit
        # impossible negative quantities.
        forecast_value = max(
            0.0,
            forecast_value,
        )

        forecast_rows.append(
            {
                "Period": (
                    f"{calendar.month_abbr[month]}, "
                    f"{year:04d}"
                ),
                measure_column: (
                    forecast_value
                ),
                "Type": "Forecast",
            }
        )

    confidence = (
        _confidence_label(
            r_squared,
            len(points),
        )
    )

    first = forecast_rows[0]
    last = forecast_rows[-1]

    answer = (
        f"Based on the most recent "
        f"{len(points)} completed monthly periods, "
        f"the {measure_column} forecast is "
        f"{_format_value(first[measure_column])} "
        f"for {first['Period']} and "
        f"{_format_value(last[measure_column])} "
        f"for {last['Period']}. "
        f"Forecast confidence is {confidence}. "
        f"The forecast uses a deterministic "
        f"linear trend model; the current partial "
        f"month is excluded."
    )

    original_sql = result.get(
        "sql"
    )

    result["answer"] = answer
    result["rows"] = forecast_rows
    result["columns"] = [
        "Period",
        measure_column,
        "Type",
    ]
    result["row_count"] = len(
        forecast_rows
    )

    result["forecast"] = {
        "method": "linear_trend",
        "horizon_months": horizon,
        "historical_periods": len(
            points
        ),
        "measure": measure_column,
        "period_column": period_column,
        "slope": slope,
        "r_squared": r_squared,
        "confidence": confidence,
        "current_partial_period_excluded": True,
    }

    result["historical_sql"] = (
        original_sql
    )

    result["warnings"] = list(
        result.get(
            "warnings"
        )
        or []
    )

    if confidence == "low":
        result["warnings"].append(
            "The historical series has weak "
            "linear trend strength. Treat this "
            "forecast as directional rather than "
            "a precise prediction."
        )

    return result
