from __future__ import annotations

import re
import calendar
from calendar import month_name
from datetime import date
from typing import Any


def normalize_text(
    value: str,
) -> str:
    return " ".join(
        str(value)
        .lower()
        .strip()
        .split()
    )


def is_numeric(
    value: Any,
) -> bool:
    return isinstance(
        value,
        (int, float),
    ) and not isinstance(
        value,
        bool,
    )


def format_value(
    value: Any,
) -> str:
    if value is None:
        return "-"

    if isinstance(
        value,
        bool,
    ):
        return (
            "Yes"
            if value
            else "No"
        )

    if isinstance(
        value,
        int,
    ):
        return f"{value:,}"

    if isinstance(
        value,
        float,
    ):
        return (
            f"{value:,.2f}"
            .rstrip("0")
            .rstrip(".")
        )

    return str(value)


def compact_number(
    value: Any,
) -> str:
    if not is_numeric(value):
        return format_value(value)

    number = float(value)

    sign = (
        "-"
        if number < 0
        else ""
    )

    absolute = abs(number)

    if absolute >= 1_000_000_000:
        return (
            f"{sign}"
            f"{absolute / 1_000_000_000:,.2f}"
            " billion"
        )

    if absolute >= 1_000_000:
        return (
            f"{sign}"
            f"{absolute / 1_000_000:,.2f}"
            " million"
        )

    if absolute >= 1_000:
        return (
            f"{sign}"
            f"{absolute / 1_000:,.2f}"
            " thousand"
        )

    return format_value(number)


def friendly_column_name(
    column: str,
) -> str:
    normalized = (
        column
        .replace("_", " ")
        .strip()
    )

    mappings = {
        "workingbalance":
            "Balance",

        "sum workingbalance":
            "Total Balance",

        "sum total price":
            "Total Fuel Cost",

        "record count":
            "Count",

        "recid":
            "Identifier",

        "customer":
            "Customer Number",

        "cocode":
            "Branch",

        "currency":
            "Currency",

        "category":
            "Account Category",
    }

    lowered = (
        normalize_text(
            normalized
        )
    )

    if lowered in mappings:
        return mappings[lowered]

    normalized = re.sub(
        r"^sum\s+",
        "Total ",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"^avg\s+",
        "Average ",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"^average\s+",
        "Average ",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"^count\s+",
        "Count ",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"^max\s+",
        "Maximum ",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"^min\s+",
        "Minimum ",
        normalized,
        flags=re.IGNORECASE,
    )

    return normalized.title()


def is_count_column(
    column: str,
) -> bool:
    normalized = (
        normalize_text(
            column
        )
        .replace(
            " ",
            "_",
        )
    )

    return (
        normalized
        in {
            "record_count",
            "count",
            "total_count",
        }
        or normalized.startswith(
            "count_"
        )
        or normalized.endswith(
            "_count"
        )
    )


def clean_count_subject(
    prompt: str,
) -> str:
    normalized = normalize_text(
        prompt
    )

    # --------------------------------------------------
    # Known business-facing subjects
    # --------------------------------------------------

    if (
        "inactive account"
        in normalized
        or "inactive accounts"
        in normalized
    ):
        return "inactive accounts"

    if (
        "active account"
        in normalized
        or "active accounts"
        in normalized
    ):
        return "active accounts"

    if (
        "customer"
        in normalized
        or "customers"
        in normalized
    ):
        return "customers"

    if (
        "account"
        in normalized
        or "accounts"
        in normalized
    ):
        return "accounts"

    if (
        "branch"
        in normalized
        or "branches"
        in normalized
    ):
        return "branches"

    if (
        "district"
        in normalized
        or "districts"
        in normalized
    ):
        return "districts"

    # --------------------------------------------------
    # Generic cleanup
    # --------------------------------------------------

    cleaned = normalized

    prefixes = [
        "how many ",
        "show me how many ",
        "tell me how many ",
        "show ",
        "display ",
        "give me ",
        "tell me ",
        "count ",
        "show me ",
    ]

    for prefix in prefixes:
        if cleaned.startswith(
            prefix
        ):
            cleaned = cleaned[
                len(prefix):
            ].strip()

            break

    # Remove common question endings.
    cleaned = re.sub(
        r"\b(?:are there|do we have|exist)\b",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"[?.!]+$",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    return (
        cleaned
        or "records"
    )


def detect_business_context(
    prompt: str,
) -> dict[str, str | None]:
    normalized = normalize_text(
        prompt
    )

    account_type = None

    if (
        "current account"
        in normalized
    ):
        account_type = (
            "Current Account"
        )

    elif (
        "saving account"
        in normalized
        or "savings account"
        in normalized
    ):
        account_type = (
            "Saving Account"
        )

    elif "deposit" in normalized:
        account_type = (
            "Deposit"
        )

    currency = None

    if " etb " in f" {normalized} ":
        currency = "ETB"

    elif " usd " in f" {normalized} ":
        currency = "USD"

    elif " eur " in f" {normalized} ":
        currency = "EUR"

    return {
        "account_type": account_type,
        "currency": currency,
    }

def detect_reporting_period(
    prompt: str,
) -> dict[str, Any] | None:
    """
    Convert common reporting-period expressions into
    business-friendly descriptions.

    Rolling month periods use completed calendar months
    and exclude the current incomplete month.
    """

    normalized = normalize_text(prompt)
    today = date.today()

    # --------------------------------------------------
    # Rolling completed months
    # last N months / past N months / previous N months
    # --------------------------------------------------

    match = re.search(
        r"\b(?:last|past|previous)\s+(\d+)\s+months?\b",
        normalized,
    )

    if match:
        months = int(match.group(1))

        if months < 1 or months > 120:
            return None

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

        last_completed_month = (
            end.month - 1
        )

        last_completed_year = end.year

        if last_completed_month == 0:
            last_completed_month = 12
            last_completed_year -= 1

        start_label = (
            f"{month_name[start.month]} "
            f"{start.year}"
        )

        end_label = (
            f"{month_name[last_completed_month]} "
            f"{last_completed_year}"
        )

        if start.year == last_completed_year:
            range_label = (
                f"{month_name[start.month]} through "
                f"{month_name[last_completed_month]} "
                f"{start.year}"
            )
        else:
            range_label = (
                f"{start_label} through {end_label}"
            )

        return {
            "type": "rolling_months",
            "months": months,
            "label": (
                f"the last {months} completed "
                f"{'month' if months == 1 else 'months'}"
            ),
            "range_label": range_label,
            "exclude_current_month": True,
        }

    # --------------------------------------------------
    # Last month
    # --------------------------------------------------

    if "last month" in normalized:
        month = today.month - 1
        year = today.year

        if month == 0:
            month = 12
            year -= 1

        return {
            "type": "last_month",
            "months": 1,
            "label": "last month",
            "range_label": (
                f"{month_name[month]} {year}"
            ),
            "exclude_current_month": True,
        }

    # --------------------------------------------------
    # This month
    # --------------------------------------------------

    if "this month" in normalized:
        return {
            "type": "this_month",
            "months": None,
            "label": "this month",
            "range_label": (
                f"{month_name[today.month]} "
                f"{today.year}"
            ),
            "exclude_current_month": False,
        }

    # --------------------------------------------------
    # Last year
    # --------------------------------------------------

    if "last year" in normalized:
        year = today.year - 1

        return {
            "type": "last_year",
            "months": 12,
            "label": "last year",
            "range_label": str(year),
            "exclude_current_month": False,
        }

    # --------------------------------------------------
    # This year
    # --------------------------------------------------

    if "this year" in normalized:
        return {
            "type": "this_year",
            "months": None,
            "label": "this year",
            "range_label": str(today.year),
            "exclude_current_month": False,
        }

    return None

def parse_time_period(value):
    """
    Detect compact numeric time periods such as:
    YYYYMM   -> month
    YYYYMMDD -> day

    Returns:
        (grain, year, period_number)
        or None
    """
    if value is None:
        return None

    try:
        text = str(int(value))
    except (TypeError, ValueError):
        return None

    if len(text) == 6:
        year = int(text[:4])
        month = int(text[4:6])

        if 1900 <= year <= 2200 and 1 <= month <= 12:
            return (
                "month",
                year,
                month,
            )

    if len(text) == 8:
        year = int(text[:4])
        month = int(text[4:6])
        day = int(text[6:8])

        try:
            date(
                year,
                month,
                day,
            )
        except ValueError:
            return None

        return (
            "day",
            year,
            (
                month,
                day,
            ),
        )

    return None


def format_time_period(parsed_period):
    if not parsed_period:
        return None

    grain = parsed_period[0]
    year = parsed_period[1]
    period = parsed_period[2]

    if grain == "month":
        return (
            f"{calendar.month_name[period]} "
            f"{year}"
        )

    if grain == "day":
        month, day = period

        return (
            f"{calendar.month_name[month]} "
            f"{day}, {year}"
        )

    return None


def is_current_time_period(parsed_period):
    if not parsed_period:
        return False

    today = date.today()

    grain = parsed_period[0]
    year = parsed_period[1]
    period = parsed_period[2]

    if grain == "month":
        return (
            year == today.year
            and period == today.month
        )

    if grain == "day":
        month, day = period

        return (
            year == today.year
            and month == today.month
            and day == today.day
        )

    return False

def generate_answer(
    prompt: str,
    columns: list[str],
    rows: list[
        dict[str, Any]
    ],
    data_source_name: str | None = None,
) -> str:
    normalized_prompt = (
        normalize_text(
            prompt
        )
    )

    context = (
        detect_business_context(
            prompt
        )
    )

    account_type = (
        context[
            "account_type"
        ]
    )

    currency = (
        context[
            "currency"
        ]
    )

    # --------------------------------------------------
    # No results
    # --------------------------------------------------

    if not rows:
        return (
            "No matching records were found "
            "for your request."
        )

    first_row = rows[0]

    # --------------------------------------------------
    # COUNT
    # --------------------------------------------------

    if (
        len(columns) == 1
        and is_count_column(
            columns[0]
        )
    ):
        count_value = (
            first_row.get(
                columns[0]
            )
        )

        subject = (
            clean_count_subject(
                prompt
            )
        )

        period = detect_reporting_period(
            prompt
        )

        # Time-aware count answer
        if (
            period is not None
            and is_numeric(count_value)
        ):
            exact_value = format_value(
                count_value
            )

            normalized = normalize_text(
                prompt
            )

            # Choose a natural business action.
            if (
                "opened" in normalized
                or "opening" in normalized
            ):
                headline = (
                    f"{exact_value} {subject} were opened "
                    f"during {period['label']}"
                )
            else:
                headline = (
                    f"The result for {period['label']} is "
                    f"{exact_value} {subject}"
                )

            if period.get(
                "range_label"
            ):
                headline += (
                    f", covering "
                    f"{period['range_label']}"
                )

            headline += "."

            details = []

            months = period.get(
                "months"
            )

            if (
                months
                and months > 1
                and count_value is not None
            ):
                monthly_average = (
                    float(count_value)
                    / months
                )

                details.append(
                    f"This represents an average of "
                    f"approximately "
                    f"{format_value(round(monthly_average))} "
                    f"{subject} per month during the period."
                )

            if period.get(
                "exclude_current_month"
            ):
                details.append(
                    "The current incomplete month is excluded "
                    "from this completed-period calculation."
                )

            if details:
                return (
                    headline
                    + " "
                    + " ".join(details)
                )

            return headline

        # Existing generic fallback
        return (
            f"There are "
            f"{format_value(count_value)} "
            f"{subject}."
        )

    # --------------------------------------------------
    # SINGLE AGGREGATED VALUE
    # --------------------------------------------------

    if (
        len(rows) == 1
        and len(columns) == 1
    ):
        column = columns[0]

        value = first_row.get(
            column
        )

        if is_numeric(value):
            if account_type:
                label = (
                    f"{account_type} Balance"
                )
            else:
                label = (
                    friendly_column_name(
                        column
                    )
                )

            exact_value = (
                format_value(
                    value
                )
            )

            compact_value = (
                compact_number(
                    value
                )
            )

            if value < 0:
                insight = (
                    "The aggregate balance is "
                    "negative."
                )
            elif value > 0:
                insight = (
                    "The aggregate balance is "
                    "positive."
                )
            else:
                insight = (
                    "The aggregate balance is zero."
                )

            currency_text = (
                f" {currency}"
                if currency
                else ""
            )

            return (
                f"{label}\n\n"
                f"The total {label.lower()} is "
                f"{compact_value}{currency_text} "
                f"({exact_value}{currency_text}).\n\n"
                f"Insight: {insight}"
            )

    # --------------------------------------------------
    # RANKING
    # --------------------------------------------------

    ranking_words = {
        "top",
        "highest",
        "largest",
        "most",
        "bottom",
        "lowest",
        "smallest",
        "least",
    }

    is_ranking = any(
        word
        in normalized_prompt.split()
        for word
        in ranking_words
    )

    if (
        is_ranking
        and len(columns) >= 2
    ):
        dimension_column = (
            columns[0]
        )

        measure_column = None

        for column in columns[1:]:
            value = (
                first_row.get(
                    column
                )
            )

            if is_numeric(value):
                measure_column = (
                    column
                )
                break

        if measure_column:
            dimension_value = (
                first_row.get(
                    dimension_column
                )
            )

            measure_value = (
                first_row.get(
                    measure_column
                )
            )

            descending = any(
                word
                in normalized_prompt.split()
                for word
                in {
                    "top",
                    "highest",
                    "largest",
                    "most",
                }
            )

            ranking_phrase = (
                "highest"
                if descending
                else "lowest"
            )

            return (
                f"{friendly_column_name(dimension_column)} "
                f"{format_value(dimension_value)} "
                f"has the {ranking_phrase} "
                f"{friendly_column_name(measure_column).lower()} "
                f"at {compact_number(measure_value)} "
                f"({format_value(measure_value)}).\n\n"
                f"{len(rows)} ranked result"
                f"{'' if len(rows) == 1 else 's'} "
                f"were returned."
            )
            
        # --------------------------------------------------
    # TIME-SERIES GROUPED RESULT
    # --------------------------------------------------

    if (
        len(columns) >= 2
        and len(rows) >= 2
    ):
        dimension_column = columns[0]

        parsed_periods = [
            parse_time_period(
                row.get(
                    dimension_column
                )
            )
            for row in rows
        ]

        # Every grouping value must represent the
        # same recognizable time grain.
        valid_periods = [
            period
            for period in parsed_periods
            if period is not None
        ]

        if (
            len(valid_periods) == len(rows)
            and len(
                {
                    period[0]
                    for period in valid_periods
                }
            ) == 1
        ):
            measure_column = None

            for column in columns[1:]:
                if all(
                    is_numeric(
                        row.get(column)
                    )
                    for row in rows
                ):
                    measure_column = column
                    break

            if measure_column:
                series = []

                for row, parsed_period in zip(
                    rows,
                    parsed_periods,
                ):
                    value = row.get(
                        measure_column
                    )

                    series.append(
                        {
                            "period": parsed_period,
                            "label": format_time_period(
                                parsed_period
                            ),
                            "value": float(value),
                            "partial": (
                                is_current_time_period(
                                    parsed_period
                                )
                            ),
                        }
                    )

                completed = [
                    item
                    for item in series
                    if not item["partial"]
                ]

                # Use completed periods for comparison
                # whenever they are available.
                comparable = (
                    completed
                    if completed
                    else series
                )

                if len(comparable) >= 2:
                    first_item = comparable[0]
                    last_item = comparable[-1]

                    highest_item = max(
                        comparable,
                        key=lambda item: item["value"],
                    )

                    lowest_item = min(
                        comparable,
                        key=lambda item: item["value"],
                    )

                    average_value = (
                        sum(
                            item["value"]
                            for item in comparable
                        )
                        / len(comparable)
                    )

                    absolute_change = (
                        last_item["value"]
                        - first_item["value"]
                    )

                    percentage_change = None

                    if first_item["value"] != 0:
                        percentage_change = (
                            absolute_change
                            / abs(first_item["value"])
                        ) * 100

                    if absolute_change > 0:
                        trend_phrase = (
                            "an upward trend"
                        )
                        change_word = "increased"
                    elif absolute_change < 0:
                        trend_phrase = (
                            "a downward trend"
                        )
                        change_word = "decreased"
                    else:
                        trend_phrase = (
                            "a broadly flat trend"
                        )
                        change_word = "remained unchanged"

                    measure_name = (
                        friendly_column_name(
                            measure_column
                        )
                    )

                    answer_parts = [
                        (
                            f"{measure_name} shows "
                            f"{trend_phrase} across "
                            f"{len(comparable)} completed "
                            f"period"
                            f"{'' if len(comparable) == 1 else 's'}."
                        ),
                        (
                            f"From {first_item['label']} "
                            f"to {last_item['label']}, "
                            f"{measure_name.lower()} "
                            f"{change_word} from "
                            f"{format_value(first_item['value'])} "
                            f"to "
                            f"{format_value(last_item['value'])}."
                        ),
                    ]

                    if percentage_change is not None:
                        answer_parts[-1] += (
                            f" This represents a "
                            f"{abs(percentage_change):,.1f}% "
                            f"{'increase' if percentage_change > 0 else 'decrease' if percentage_change < 0 else 'change'}."
                        )

                    answer_parts.append(
                        (
                            f"The highest completed period "
                            f"was {highest_item['label']} "
                            f"at "
                            f"{format_value(highest_item['value'])}, "
                            f"while the lowest was "
                            f"{lowest_item['label']} "
                            f"at "
                            f"{format_value(lowest_item['value'])}."
                        )
                    )

                    answer_parts.append(
                        (
                            f"The average across completed "
                            f"periods was approximately "
                            f"{format_value(round(average_value))}."
                        )
                    )

                    partial_items = [
                        item
                        for item in series
                        if item["partial"]
                    ]

                    if partial_items:
                        partial_item = (
                            partial_items[-1]
                        )

                        answer_parts.append(
                            (
                                f"{partial_item['label']} "
                                f"currently stands at "
                                f"{format_value(partial_item['value'])}, "
                                f"but it is an incomplete "
                                f"period and is excluded from "
                                f"the completed-period trend "
                                f"comparison."
                            )
                        )

                    return "\n\n".join(
                        answer_parts
                    )

    # --------------------------------------------------
    # GROUPED RESULT
    # --------------------------------------------------

    if (
        len(columns) >= 2
        and len(rows) >= 1
    ):
        dimension_column = (
            columns[0]
        )

        measure_column = None

        for column in columns[1:]:
            value = (
                first_row.get(
                    column
                )
            )

            if is_numeric(value):
                measure_column = (
                    column
                )
                break

        if measure_column:
            dimension_value = (
                first_row.get(
                    dimension_column
                )
            )

            measure_value = (
                first_row.get(
                    measure_column
                )
            )

            return (
                f"I found {len(rows)} grouped "
                f"result"
                f"{'' if len(rows) == 1 else 's'} "
                f"by "
                f"{friendly_column_name(dimension_column).lower()}.\n\n"
                f"The first result is "
                f"{format_value(dimension_value)} "
                f"with "
                f"{compact_number(measure_value)} "
                f"({format_value(measure_value)})."
            )

    # --------------------------------------------------
    # DETAIL / LIST RESULT
    # --------------------------------------------------

    source_text = (
        f" from {data_source_name}"
        if data_source_name
        else ""
    )

    return (
        f"I found {len(rows)} matching "
        f"record"
        f"{'' if len(rows) == 1 else 's'}"
        f"{source_text}."
    )