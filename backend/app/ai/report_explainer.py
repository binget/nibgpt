import json
from decimal import Decimal, InvalidOperation

from app.ai.providers.factory import (
    get_ai_provider,
)


REPORT_SYSTEM_PROMPT = """
You are NIBGPT's Banking Report Analysis Agent.

You receive VERIFIED FACTS calculated by NIBGPT's governed
reporting engine.

Your job is only to explain those facts in clear business language.

STRICT RULES:

1. Never calculate rankings yourself.
2. Never decide which row is highest or lowest yourself.
3. Never invent numbers.
4. Never invent percentages.
5. Never invent increases, decreases, growth or decline.
6. Never claim a trend unless VERIFIED FACTS explicitly says
   time-series analysis is available.
7. Never invent causes such as economic conditions, marketing,
   branch performance, operational problems or customer behavior.
8. Never change entity names.
9. Never change currencies or add a currency symbol unless the
   verified facts explicitly contain a currency.
10. Never repeat the complete table.
11. Use only VERIFIED FACTS.
12. If a conclusion is not present in VERIFIED FACTS, do not make it.
13. The user can already see the detailed report table.

- If analysis_allowed is false, say only that there is not enough governed report data to analyze.
- NEVER substitute remembered examples or previous values when report data is missing.
- NEVER create sample branch, district, balance, count, or ranking data.

Write a short management-level interpretation.

Normally provide 2 to 4 observations.

Do not create sections for:
- highest
- lowest
- growth
- decline

unless those facts were explicitly supplied.

Never describe a balance difference as growth or decline.
""".strip()


def to_decimal(
    value,
) -> Decimal | None:
    if value is None:
        return None

    try:
        cleaned = str(
            value
        ).replace(
            ",",
            "",
        ).strip()

        if not cleaned:
            return None

        return Decimal(
            cleaned
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return None


def detect_numeric_column(
    columns: list[str],
    rows: list[dict],
) -> str | None:
    if not rows:
        return None

    # Prefer columns that look like measures.
    preferred_words = (
        "balance",
        "amount",
        "total",
        "value",
        "count",
        "volume",
    )

    for column in columns:
        lower = (
            column
            .lower()
        )

        if any(
            word in lower
            for word in preferred_words
        ):
            valid_count = sum(
                1
                for row in rows
                if to_decimal(
                    row.get(column)
                )
                is not None
            )

            if valid_count:
                return column

    # Fallback: first mostly-numeric column.
    for column in columns:
        valid_count = sum(
            1
            for row in rows
            if to_decimal(
                row.get(column)
            )
            is not None
        )

        if (
            valid_count
            >= max(
                1,
                len(rows) // 2,
            )
        ):
            return column

    return None


def detect_dimension_column(
    columns: list[str],
    numeric_column: str | None,
) -> str | None:
    for column in columns:
        if (
            column
            != numeric_column
        ):
            return column

    return None


def build_verified_facts(
    report: dict,
) -> dict:
    
    if (
        not report.get("success")
        or not rows
        or not columns
    ):
        return {
            "report_available": False,
            "analysis_allowed": False,
            "reason": (
                "No valid governed report data "
                "was provided."
            ),
        }
    rows = (
        report.get("rows")
        or []
    )

    columns = (
        report.get("columns")
        or []
    )

    facts = {
        "report_question":
            report.get("prompt"),

        "row_count":
            report.get(
                "row_count",
                len(rows),
            ),
        
        "report_available": True,
        "analysis_allowed": True,

        "columns":
            columns,

        "time_series":
            False,

        "currency":
            None,

        "highest":
            None,

        "lowest":
            None,

        "top_3":
            [],

        "total":
            None,
    }

    if (
        not rows
        or not columns
    ):
        return facts

    numeric_column = (
        detect_numeric_column(
            columns,
            rows,
        )
    )

    dimension_column = (
        detect_dimension_column(
            columns,
            numeric_column,
        )
    )

    if (
        numeric_column is None
        or dimension_column is None
    ):
        return facts

    numeric_rows = []

    for row in rows:
        numeric_value = (
            to_decimal(
                row.get(
                    numeric_column
                )
            )
        )

        if numeric_value is None:
            continue

        numeric_rows.append(
            {
                "name":
                    str(
                        row.get(
                            dimension_column,
                            ""
                        )
                    ),

                "value":
                    numeric_value,
            }
        )

    if not numeric_rows:
        return facts

    sorted_rows = sorted(
        numeric_rows,
        key=lambda item:
            item["value"],
        reverse=True,
    )

    highest = (
        sorted_rows[0]
    )

    lowest = (
        sorted_rows[-1]
    )

    total = sum(
        (
            item["value"]
            for item
            in sorted_rows
        ),
        Decimal("0"),
    )

    facts[
        "dimension"
    ] = dimension_column

    facts[
        "measure"
    ] = numeric_column

    facts[
        "highest"
    ] = {
        "name":
            highest["name"],
        "value":
            str(
                highest["value"]
            ),
    }

    facts[
        "lowest"
    ] = {
        "name":
            lowest["name"],
        "value":
            str(
                lowest["value"]
            ),
    }

    facts[
        "top_3"
    ] = [
        {
            "name":
                item["name"],
            "value":
                str(
                    item["value"]
                ),
        }
        for item
        in sorted_rows[:3]
    ]

    facts[
        "total"
    ] = str(
        total
    )

    if total != 0:
        facts[
            "highest_share_percent"
        ] = str(
            round(
                (
                    highest["value"]
                    / total
                )
                * Decimal("100"),
                2,
            )
        )

        top_three_total = sum(
            (
                item["value"]
                for item
                in sorted_rows[:3]
            ),
            Decimal("0"),
        )

        facts[
            "top_3_share_percent"
        ] = str(
            round(
                (
                    top_three_total
                    / total
                )
                * Decimal("100"),
                2,
            )
        )

    return facts


def build_explanation_prompt(
    report: dict,
) -> str:
    facts = (
        build_verified_facts(
            report
        )
    )

    return (
        "Analyze this banking report using ONLY "
        "the VERIFIED FACTS below.\n\n"

        "Do not perform your own calculations. "
        "Do not infer growth, decline, trends, causes, "
        "currency, performance or economic explanations.\n\n"

        "VERIFIED FACTS:\n"
        f"{json.dumps(facts, default=str, indent=2)}"
    )


def explain_report(
    report: dict,
) -> str:
    provider = (
        get_ai_provider()
    )

    return provider.generate(
        prompt=(
            build_explanation_prompt(
                report
            )
        ),
        system_prompt=(
            REPORT_SYSTEM_PROMPT
        ),
    )


def stream_report_explanation(
    report: dict,
):
    provider = (
        get_ai_provider()
    )

    yield from provider.stream(
        prompt=(
            build_explanation_prompt(
                report
            )
        ),
        system_prompt=(
            REPORT_SYSTEM_PROMPT
        ),
    )