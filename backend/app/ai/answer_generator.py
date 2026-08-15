from __future__ import annotations

import re
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
    )


def clean_count_subject(
    prompt: str,
) -> str:
    normalized = normalize_text(
        prompt
    )

    for prefix in [
        "show ",
        "display ",
        "give me ",
        "tell me ",
        "count ",
        "show me ",
    ]:
        if normalized.startswith(
            prefix
        ):
            normalized = (
                normalized[
                    len(prefix):
                ]
            )
            break

    return normalized.strip()


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