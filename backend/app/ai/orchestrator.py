import re
from dataclasses import dataclass


@dataclass
class OrchestratorDecision:
    route: str
    confidence: int
    reason: str


REPORT_TERMS = {
    "show",
    "report",
    "balance",
    "accounts",
    "account",
    "branch",
    "district",
    "customer",
    "currency",
    "deposit",
    "amount",
    "number",
    "how many",
    "top",
    "bottom",
}


KNOWLEDGE_TERMS = {
    "policy",
    "procedure",
    "manual",
    "directive",
    "circular",
    "guideline",
    "document",
}

FOLLOW_UP_TERMS = {
    "top",
    "bottom",
    "only",
    "now",
    "instead",
    "same",
    "active",
    "inactive",

    "branch",
    "district",
    "customer",
    "currency",

    "ascending",
    "descending",

    "highest",
    "lowest",

    "today",
    "yesterday",

    "usd",
    "eur",
    "gbp",
    "etb",
    "birr",
}

def extract_reporting_context(
    prompt: str,
) -> dict:
    original = (
        " ".join(
            prompt.strip().split()
        )
    )

    normalized = (
        original.lower()
    )

    context = {
        "measure": None,
        "dimension": None,
        "status": None,
        "ranking": None,
        "limit": None,

        "sort_direction": None,

        "district": None,
        "branch": None,
        "currency": None,
        "customer": None,
        "category": None,

        "date_from": None,
        "date_to": None,
        "period": None,

        "filters": {},

        "previous_prompt": original,
    }

    # ==================================================
    # Measure
    # ==================================================

    if (
        "balance" in normalized
        and (
            "number" in normalized
            or "how many" in normalized
            or "count" in normalized
        )
    ):
        context["measure"] = (
            "count_and_balance"
        )

    elif "balance" in normalized:
        context["measure"] = (
            "balance"
        )

    elif (
        "number" in normalized
        or "how many" in normalized
        or "count" in normalized
    ):
        context["measure"] = (
            "count"
        )

    # ==================================================
    # Dimension
    # ==================================================

    if "branch" in normalized:
        context["dimension"] = (
            "branch"
        )

    elif "district" in normalized:
        context["dimension"] = (
            "district"
        )

    elif "customer" in normalized:
        context["dimension"] = (
            "customer"
        )

    elif "currency" in normalized:
        context["dimension"] = (
            "currency"
        )

    # ==================================================
    # Status
    # ==================================================

    if "inactive" in normalized:
        context["status"] = (
            "inactive"
        )

    elif "active" in normalized:
        context["status"] = (
            "active"
        )

    # ==================================================
    # Ranking
    # ==================================================

    if (
        "top" in normalized
        or "highest" in normalized
        or "largest" in normalized
        or "most" in normalized
    ):
        context["ranking"] = (
            "top"
        )

    elif (
        "bottom" in normalized
        or "lowest" in normalized
        or "smallest" in normalized
        or "least" in normalized
    ):
        context["ranking"] = (
            "bottom"
        )

    # ==================================================
    # Limit
    # ==================================================

    limit_match = re.search(
        r"\b(?:top|bottom|first|last)\s+(\d+)\b",
        normalized,
    )

    if limit_match:
        context["limit"] = int(
            limit_match.group(1)
        )

    # ==================================================
    # Sort direction
    # ==================================================

    if (
        "lowest to highest"
        in normalized
        or "ascending"
        in normalized
        or "asc order"
        in normalized
        or "smallest to largest"
        in normalized
    ):
        context["sort_direction"] = (
            "ascending"
        )

    elif (
        "highest to lowest"
        in normalized
        or "descending"
        in normalized
        or "desc order"
        in normalized
        or "largest to smallest"
        in normalized
    ):
        context["sort_direction"] = (
            "descending"
        )

    # ==================================================
    # Currency
    # ==================================================

    currency_map = {
        "usd": "USD",
        "dollar": "USD",
        "dollars": "USD",

        "eur": "EUR",
        "euro": "EUR",
        "euros": "EUR",

        "gbp": "GBP",
        "pound": "GBP",
        "pounds": "GBP",

        "etb": "ETB",
        "birr": "ETB",

        "aed": "AED",

        "jpy": "JPY",
        "yen": "JPY",
    }

    for keyword, code in (
        currency_map.items()
    ):
        if re.search(
            rf"\b{re.escape(keyword)}\b",
            normalized,
        ):
            context["currency"] = code
            context["filters"][
                "currency"
            ] = code

            break

    # ==================================================
    # Period
    # ==================================================

    period_map = {
        "today": "today",
        "yesterday": "yesterday",
        "this month": "this_month",
        "last month": "last_month",
        "this year": "this_year",
        "last year": "last_year",
    }

    for phrase, period in (
        period_map.items()
    ):
        if phrase in normalized:
            context["period"] = (
                period
            )

            break

    # ==================================================
    # Explicit district filter
    #
    # Examples:
    # only Addis Ababa district
    # for West Addis Ababa District
    # in Hawassa District
    # ==================================================

    district_match = re.search(
        r"\b(?:only|for|in)\s+"
        r"(.+?\bdistrict)\b",
        original,
        flags=re.IGNORECASE,
    )

    if district_match:
        district = (
            district_match
            .group(1)
            .strip()
        )

        context["district"] = (
            district
        )

        context["filters"][
            "district"
        ] = district

    # ==================================================
    # Explicit branch filter
    # ==================================================

    branch_match = re.search(
        r"\b(?:only|for|in)\s+"
        r"(.+?\bbranch)\b",
        original,
        flags=re.IGNORECASE,
    )

    if branch_match:
        branch = (
            branch_match
            .group(1)
            .strip()
        )

        context["branch"] = (
            branch
        )

        context["filters"][
            "branch"
        ] = branch
        
        # ==================================================
    # Normalize ranking/sorting behavior
    # ==================================================

    if context["ranking"] == "top":
        context["sort_direction"] = (
            "descending"
        )

    elif context["ranking"] == "bottom":
        context["sort_direction"] = (
            "ascending"
        )

    # Explicit sorting without top/bottom means
    # normal sorting, not a ranking restriction.
    if (
        context["sort_direction"]
        and context["ranking"] is None
    ):
        context["limit"] = None

    return context



def merge_reporting_context(
    previous_context: dict | None,
    prompt: str,
) -> dict:
    current = (
        extract_reporting_context(
            prompt
        )
    )

    if not previous_context:
        return current

    merged = dict(
        previous_context
    )

    for key in [
        "measure",
        "dimension",
        "status",
        "ranking",
        "limit",
        "sort_direction",
        "district",
        "branch",
        "currency",
        "customer",
        "category",
        "date_from",
        "date_to",
        "period",
    ]:
        if (
            current.get(key)
            is not None
        ):
            merged[key] = (
                current[key]
            )

    previous_filters = dict(
        previous_context.get(
            "filters"
        )
        or {}
    )

    current_filters = dict(
        current.get(
            "filters"
        )
        or {}
    )

    previous_filters.update(
        current_filters
    )

    merged["filters"] = (
        previous_filters
    )

    merged[
        "previous_prompt"
    ] = prompt

    return merged

def build_prompt_from_context(
    context: dict,
) -> str:
    parts = []

    measure = context.get(
        "measure"
    )

    dimension = context.get(
        "dimension"
    )

    status = context.get(
        "status"
    )

    ranking = context.get(
        "ranking"
    )

    limit = context.get(
        "limit"
    )

    sort_direction = context.get(
        "sort_direction"
    )

    district = context.get(
        "district"
    )

    branch = context.get(
        "branch"
    )

    currency = context.get(
        "currency"
    )

    period = context.get(
        "period"
    )

    # ==================================================
    # Measure
    # ==================================================

    if measure == "count_and_balance":
        parts.append(
            "Show number and total balance "
            "of deposit accounts"
        )

    elif measure == "balance":
        parts.append(
            "Show total deposit balance"
        )

    elif measure == "count":
        parts.append(
            "Show number of deposit accounts"
        )

    else:
        parts.append(
            "Show report"
        )

    # ==================================================
    # Status
    # ==================================================

    if status:
        parts.append(
            f"for {status} accounts"
        )

    # ==================================================
    # Dimension
    # ==================================================

    if dimension:
        parts.append(
            f"by {dimension}"
        )

    # ==================================================
    # Filters
    # ==================================================

    if district:
        parts.append(
            f"for district {district}"
        )

    if branch:
        parts.append(
            f"for branch {branch}"
        )

    if currency:
        parts.append(
            f"for currency {currency}"
        )

    if period:
        readable_period = (
            period.replace(
                "_",
                " ",
            )
        )

        parts.append(
            f"for {readable_period}"
        )

    # ==================================================
    # Ranking
    # ==================================================

    if (
        ranking
        and limit
    ):
        parts.append(
            f"{ranking} {limit}"
        )

    elif ranking:
        parts.append(
            ranking
        )
        
        # ==================================================
    # Ranking and limit
    # ==================================================

    if ranking == "top":
        if limit:
            parts.append(
                f"return only the top {limit} "
                "results by the selected measure"
            )
        else:
            parts.append(
                "order by the selected measure "
                "from highest to lowest"
            )

    elif ranking == "bottom":
        if limit:
            parts.append(
                f"return only the bottom {limit} "
                "results by the selected measure"
            )
        else:
            parts.append(
                "order by the selected measure "
                "from lowest to highest"
            )

    # ==================================================
    # Explicit sorting
    # ==================================================

    if sort_direction == "ascending":
        parts.append(
            "sort the results by the selected "
            "measure from lowest to highest"
        )

    elif sort_direction == "descending":
        parts.append(
            "sort the results by the selected "
            "measure from highest to lowest"
        )

    # ==================================================
    # Sorting
    # ==================================================

    if (
        sort_direction
        == "ascending"
    ):
        parts.append(
            "ordered from lowest "
            "to highest"
        )

    elif (
        sort_direction
        == "descending"
    ):
        parts.append(
            "ordered from highest "
            "to lowest"
        )

    return " ".join(
        parts
    ).strip()
    


def is_follow_up_prompt(
    prompt: str,
) -> bool:
    normalized = (
        prompt.strip().lower()
    )

    words = normalized.split()

    # Short prompts are often follow-ups.
    if len(words) <= 6:
        if any(
            term in normalized
            for term in FOLLOW_UP_TERMS
        ):
            return True

    return False


def build_contextual_prompt(
    prompt: str,
    previous_prompt: str | None,
) -> str:
    if not previous_prompt:
        return prompt

    if not is_follow_up_prompt(
        prompt
    ):
        return prompt

    return (
        f"{previous_prompt}. "
        f"Follow-up instruction: "
        f"{prompt}"
    )


def classify_prompt(
    prompt: str,
) -> OrchestratorDecision:
    normalized = (
        prompt.strip().lower()
    )

    knowledge_score = 0
    report_score = 0

    for term in KNOWLEDGE_TERMS:
        if term in normalized:
            knowledge_score += 1

    for term in REPORT_TERMS:
        if term in normalized:
            report_score += 1

    if knowledge_score > report_score:
        return OrchestratorDecision(
            route="knowledge",
            confidence=85,
            reason=(
                "The prompt appears to request "
                "institutional knowledge."
            ),
        )

    if report_score > 0:
        return OrchestratorDecision(
            route="reporting",
            confidence=90,
            reason=(
                "The prompt appears to request "
                "governed business data."
            ),
        )

    return OrchestratorDecision(
        route="general",
        confidence=70,
        reason=(
            "No strong reporting or knowledge "
            "intent was detected."
        ),
    )