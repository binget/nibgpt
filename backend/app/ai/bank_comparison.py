from datetime import (
    datetime,
    timezone,
)

from app.ai.web_intelligence import (
    get_nib_public_pages,
)

from app.ai.competitor_intelligence import (
    detect_competitors,
    detect_competitor_product_request,
    extract_competitor_product_facts,
    select_competitor_pages,
)


NIB_ALIASES = (
    "nib",
    "nib international bank",
)

DIGITAL_CAPABILITIES = {
    "Mobile Banking": (
        "mobile banking",
        "mobile app",
        "mobile application",
        "nibtera",
    ),

    "Internet Banking": (
        "internet banking",
        "online banking",
        "nibtera online",
    ),

    "Digital Wallet": (
        "digital wallet",
        "wallet",
        "cbe birr",
    ),

    "USSD Banking": (
        "ussd",
    ),

    "Card Services": (
        "card service",
        "card services",
        "debit card",
        "credit card",
        "card control",
        "cards",
    ),

    "Transfers": (
        "fund transfer",
        "funds transfer",
        "money transfer",
        "transfer money",
        "transfers",
    ),

    "Payments": (
        "bill payment",
        "bill payments",
        "payments",
        "merchant payment",
    ),

    "Airtime": (
        "airtime",
        "mobile top up",
        "mobile top-up",
        "top up",
        "top-up",
    ),

    "Account Management": (
        "account management",
        "manage account",
        "manage accounts",
        "account balance",
        "balance inquiry",
    ),

    "Security / 2FA": (
        "two-factor",
        "two factor",
        "2fa",
        "otp",
        "one-time password",
    ),
}

LOAN_CAPABILITIES = {
    "Personal / Consumer Loans": (
        "personal loan",
        "consumer loan",
        "consumer credit",
        "consumer financing",
    ),

    "Business Loans": (
        "business loan",
        "business credit",
        "business financing",
        "commercial loan",
    ),

    "SME Financing": (
        "sme loan",
        "sme financing",
        "small and medium",
        "small business",
        "medium enterprise",
    ),

    "Agriculture Financing": (
        "agriculture loan",
        "agricultural loan",
        "agriculture financing",
        "agricultural financing",
        "agriculture",
    ),

    "Construction Financing": (
        "construction loan",
        "construction financing",
        "building and construction",
        "construction",
    ),

    "Trade Financing": (
        "trade finance",
        "trade financing",
        "import financing",
        "export financing",
        "import",
        "export",
    ),

    "Vehicle / Transport Financing": (
        "vehicle loan",
        "vehicle financing",
        "transport loan",
        "transport financing",
        "transport",
    ),

    "Mortgage / Housing": (
        "mortgage",
        "housing loan",
        "home loan",
        "house loan",
        "housing",
    ),

    "Overdraft": (
        "overdraft",
        "over draft",
    ),

    "Term Loan": (
        "term loan",
        "medium term loan",
        "long term loan",
        "short term loan",
    ),
}


DEPOSIT_CAPABILITIES = {
    "Savings Account": (
        "savings account",
        "saving account",
    ),

    "Current Account": (
        "current account",
        "demand deposit",
    ),

    "Fixed / Time Deposit": (
        "fixed deposit",
        "time deposit",
        "term deposit",
    ),

    "Youth / Children Account": (
        "youth account",
        "children account",
        "child account",
        "minor account",
    ),

    "Diaspora Account": (
        "diaspora account",
        "diaspora deposit",
    ),

    "Business Account": (
        "business account",
        "corporate account",
    ),

    "Foreign Currency Account": (
        "foreign currency account",
        "foreign currency deposit",
        "fc account",
    ),
}


TRADE_CAPABILITIES = {
    "Letter of Credit": (
        "letter of credit",
        "letters of credit",
        "documentary credit",
    ),

    "Bank Guarantee": (
        "bank guarantee",
        "guarantee service",
        "guarantees",
    ),

    "Documentary Collection": (
        "documentary collection",
        "document collection",
    ),

    "Import Services": (
        "import service",
        "import services",
        "import trade",
    ),

    "Export Services": (
        "export service",
        "export services",
        "export trade",
    ),

    "Advance Payment": (
        "advance payment",
    ),

    "Trade Financing": (
        "trade financing",
        "trade finance",
    ),
}


IFB_CAPABILITIES = {
    "Interest-Free Deposit": (
        "interest free deposit",
        "interest-free deposit",
        "sharia compliant deposit",
        "sharia-compliant deposit",
    ),

    "Interest-Free Financing": (
        "interest free financing",
        "interest-free financing",
        "sharia financing",
    ),

    "Murabaha": (
        "murabaha",
    ),

    "Mudarabah": (
        "mudarabah",
        "mudharabah",
    ),

    "Wadiah": (
        "wadiah",
        "wadi'ah",
        "wadia",
    ),

    "Ijara": (
        "ijara",
        "ijarah",
    ),

    "Salam": (
        "salam financing",
        "bai salam",
        "bai' salam",
    ),

    "Istisna": (
        "istisna",
        "istisna'a",
    ),
}


FOREX_CAPABILITIES = {
    "Foreign Currency Exchange": (
        "foreign exchange",
        "currency exchange",
        "forex service",
    ),

    "Foreign Currency Account": (
        "foreign currency account",
        "fc account",
    ),

    "Forex Bureau": (
        "forex bureau",
        "forex bureaus",
    ),

    "International Transfer": (
        "international transfer",
        "international money transfer",
    ),

    "Remittance": (
        "remittance",
        "money transfer",
    ),

    "SWIFT": (
        "swift transfer",
        "swift payment",
        "swift",
    ),
}

COMPARISON_CAPABILITIES = {
    "digital_banking":
        DIGITAL_CAPABILITIES,

    "loan":
        LOAN_CAPABILITIES,

    "deposit":
        DEPOSIT_CAPABILITIES,

    "trade":
        TRADE_CAPABILITIES,

    "interest_free":
        IFB_CAPABILITIES,

    "forex":
        FOREX_CAPABILITIES,
}


COMPARISON_LABELS = {
    "digital_banking":
        "Digital Banking",

    "loan":
        "Loan Products",

    "deposit":
        "Deposit Products",

    "trade":
        "Trade Finance",

    "interest_free":
        "Interest-Free Banking",

    "forex":
        "Foreign Exchange",
}

def detect_capabilities(
    pages: list[dict],
    capabilities: dict[
        str,
        tuple[str, ...],
    ],
) -> dict[str, bool]:

    # Search both:
    # 1. Retrieved page content
    # 2. Page URLs
    #
    # Some banking websites render generic page text
    # while the product name exists only in the URL.

    combined_text = "\n".join(
        page.get("text") or ""
        for page in pages
    ).lower()

    combined_urls = "\n".join(
        page.get("url") or ""
        for page in pages
    ).lower()

    # Normalize URL separators.
    normalized_urls = (
        combined_urls
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
    )

    searchable_content = (
        combined_text
        + "\n"
        + normalized_urls
    )

    result = {}

    for capability, terms in (
        capabilities.items()
    ):
        result[capability] = any(
            term.lower()
            .replace("-", " ")
            .replace("_", " ")
            in searchable_content
            for term in terms
        )

    return result

def build_capability_matrix(
    nib_pages: list[dict],
    competitor_pages: list[dict],
    competitor_name: str,
    capabilities: dict[
        str,
        tuple[str, ...],
    ],
) -> str:

    nib = detect_capabilities(
        nib_pages,
        capabilities,
    )

    competitor = detect_capabilities(
        competitor_pages,
        capabilities,
    )

    rows = []

    for capability in capabilities:
        nib_value = (
            "✓"
            if nib.get(
                capability,
                False,
            )
            else "?"
        )

        competitor_value = (
            "✓"
            if competitor.get(
                capability,
                False,
            )
            else "?"
        )

        rows.append(
            f"| {capability} "
            f"| {nib_value} "
            f"| {competitor_value} |"
        )

    return (
        "| Capability | NIB | "
        f"{competitor_name} |\n"
        "|---|:---:|:---:|\n"
        + "\n".join(rows)
    )


def normalize_text(
    text: str,
) -> str:
    return " ".join(
        text.lower().split()
    )

def build_key_findings(
    nib_pages: list[dict],
    competitor_pages: list[dict],
    competitor_name: str,
    capabilities: dict[
        str,
        tuple[str, ...],
    ],
) -> str:

    nib = detect_capabilities(
        nib_pages,
        capabilities,
    )

    competitor = detect_capabilities(
        competitor_pages,
        capabilities,
    )

    shared = []
    nib_confirmed = []
    competitor_confirmed = []

    for capability in capabilities:
        nib_has = nib.get(
            capability,
            False,
        )

        competitor_has = (
            competitor.get(
                capability,
                False,
            )
        )

        if nib_has and competitor_has:
            shared.append(
                capability
            )

        elif nib_has:
            nib_confirmed.append(
                capability
            )

        elif competitor_has:
            competitor_confirmed.append(
                capability
            )

    findings = []

    if shared:
        findings.append(
            "- Both banks have confirmed evidence "
            "for: "
            + ", ".join(shared)
            + "."
        )

    if nib_confirmed:
        findings.append(
            "- The retrieved NIB sources additionally "
            "confirm: "
            + ", ".join(
                nib_confirmed
            )
            + "."
        )

    if competitor_confirmed:
        findings.append(
            f"- The retrieved {competitor_name} "
            "sources additionally confirm: "
            + ", ".join(
                competitor_confirmed
            )
            + "."
        )

    if not findings:
        return (
            "- The retrieved official sources do not "
            "contain enough matching information for "
            "confirmed findings."
        )

    return "\n".join(
        findings
    )

def is_bank_comparison_question(
    question: str,
) -> bool:
    normalized = normalize_text(
        question
    )

    competitors = (
        detect_competitors(
            question
        )
    )

    if not competitors:
        return False

    mentions_nib = any(
        alias in normalized
        for alias in NIB_ALIASES
    )

    comparison_terms = (
        "compare",
        "comparison",
        "compared",
        "versus",
        " vs ",
        "difference",
        "differences",
        "better than",
        "how does",
        "what does",
        "does not",
        "doesn't",
    )

    has_comparison_intent = any(
        term in normalized
        for term in comparison_terms
    )

    return (
        mentions_nib
        and has_comparison_intent
    )


def extract_nib_comparison_facts(
    question: str,
    pages: list[dict],
) -> list[str]:
    product_type = (
        detect_competitor_product_request(
            question
        )
    )

    keywords = {
        "digital_banking": (
            "internet banking",
            "mobile banking",
            "nibtera",
            "ussd",
            "atm",
            "pos",
            "card",
            "wallet",
            "transfer",
            "payment",
            "airtime",
            "2fa",
        ),

        "loan": (
            "loan",
            "loans",
            "credit",
            "financing",
        ),

        "deposit": (
            "deposit",
            "saving",
            "savings",
            "current account",
            "fixed deposit",
        ),

        "trade": (
            "trade",
            "letter of credit",
            "documentary",
            "guarantee",
            "lc",
        ),

        "interest_free": (
            "interest free",
            "interest-free",
            "ifb",
            "halal",
            "sharia",
        ),

        "forex": (
            "forex",
            "foreign exchange",
            "currency",
        ),
    }

    wanted = keywords.get(
        product_type,
        (),
    )

    if not wanted:
        return []

    blocked = (
        "useful links",
        "copyright",
        "privacy",
        "cookie",
        "contact form",
        "complaint form",
        "vacancy",
        "download our mobile app",
    )

    facts = []
    seen = set()

    for page in pages:
        text = (
            page.get("text")
            or ""
        )

        for raw_line in text.splitlines():
            line = " ".join(
                raw_line.split()
            )

            if not line:
                continue

            lowered = line.lower()

            if any(
                bad in lowered
                for bad in blocked
            ):
                continue

            if not any(
                keyword in lowered
                for keyword in wanted
            ):
                continue

            if len(line) > 250:
                continue

            key = lowered

            if key in seen:
                continue

            seen.add(key)
            facts.append(line)

            if len(facts) >= 12:
                return facts

    return facts


def clean_fact(
    fact: str,
) -> str:
    fact = " ".join(
        fact.split()
    )

    # Remove common heading-like noise.
    prefixes = (
        "product features:",
        "unique features:",
    )

    lowered = fact.lower()

    for prefix in prefixes:
        if lowered == prefix:
            return ""

    return fact


def deduplicate_facts(
    facts: list[str],
) -> list[str]:
    result = []
    seen = set()

    for fact in facts:
        fact = clean_fact(
            fact
        )

        if not fact:
            continue

        normalized = (
            normalize_text(
                fact
            )
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            fact
        )

    return result


def build_source_list(
    nib_pages: list[dict],
    competitor_pages: list[dict],
) -> list[dict]:
    sources = []
    seen = set()

    for page in nib_pages:
        url = page.get("url")

        if (
            not url
            or url in seen
        ):
            continue

        seen.add(url)

        sources.append(
            {
                "title":
                    page.get("title")
                    or "Nib International Bank",

                "url":
                    url,

                "bank_name":
                    "Nib International Bank",

                "trust_level":
                    "official",
            }
        )

    for page in competitor_pages:
        url = page.get("url")

        if (
            not url
            or url in seen
        ):
            continue

        seen.add(url)

        sources.append(
            {
                "title":
                    page.get("title")
                    or page.get("bank_name"),

                "url":
                    url,

                "bank_name":
                    page.get("bank_name"),

                "trust_level":
                    "official",
            }
        )

    return sources


def answer_bank_comparison(
    question: str,
) -> dict:
    competitors = (
        detect_competitors(
            question
        )
    )

    if not competitors:
        return {
            "success": False,
            "answer": (
                "No approved competitor "
                "was identified."
            ),
            "sources": [],
            "warnings": [],
            "retrieved_at": None,
        }

    # Start with one competitor.
    competitor = competitors[0]

    # -------------------------------
    # NIB evidence
    # -------------------------------

    nib_pages = (
        get_nib_public_pages(
            question=question
        )
    )

    nib_facts = (
        extract_nib_comparison_facts(
            question=question,
            pages=nib_pages,
        )
    )

    nib_facts = (
        deduplicate_facts(
            nib_facts
        )
    )

    # -------------------------------
    # Competitor evidence
    # -------------------------------

    competitor_pages = (
        select_competitor_pages(
            question=question,
            source=competitor,
            maximum_pages=2,
        )
    )

    competitor_facts = (
        extract_competitor_product_facts(
            question=question,
            pages=competitor_pages,
        )
    )

    competitor_facts = (
        deduplicate_facts(
            competitor_facts
        )
    )

    if (
        not nib_facts
        and not competitor_facts
    ):
        return {
            "success": False,
            "answer": (
                "The official public sources "
                "did not provide enough information "
                "for this comparison."
            ),
            "sources":
                build_source_list(
                    nib_pages,
                    competitor_pages,
                ),
            "warnings": [],
            "retrieved_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

    # Keep comparison readable.
    nib_facts = nib_facts[:8]
    competitor_facts = (
        competitor_facts[:8]
    )

    nib_section = "\n".join(
        f"- {fact}"
        for fact in nib_facts
    )

    competitor_section = "\n".join(
        f"- {fact}"
        for fact in competitor_facts
    )

    if not nib_section:
        nib_section = (
            "- No matching information "
            "was found in the retrieved "
            "official NIB content."
        )

    if not competitor_section:
        competitor_section = (
            "- No matching information "
            "was found in the retrieved "
            f"official {competitor.name} content."
        )

    product_type = (
        detect_competitor_product_request(
            question
        )
    )

    labels = {
        "digital_banking":
            "Digital Banking",

        "loan":
            "Loan Products",

        "deposit":
            "Deposit Products",

        "trade":
            "Trade Finance",

        "interest_free":
            "Interest-Free Banking",

        "forex":
            "Foreign Exchange",
    }

    topic = labels.get(
        product_type,
        "Banking Services",
    )

    capabilities = (
        COMPARISON_CAPABILITIES.get(
            product_type
        )
    )

    if capabilities:

        matrix = build_capability_matrix(
            nib_pages=nib_pages,
            competitor_pages=competitor_pages,
            competitor_name=competitor.name,
            capabilities=capabilities,
        )

        key_findings = build_key_findings(
            nib_pages=nib_pages,
            competitor_pages=competitor_pages,
            competitor_name=competitor.name,
            capabilities=capabilities,
        )

        topic = COMPARISON_LABELS.get(
            product_type,
            "Banking Services",
        )

        answer = (
            f"**NIB vs {competitor.name} — "
            f"{topic}**\n\n"

            f"{matrix}\n\n"

            "**Key Findings**\n\n"
            f"{key_findings}\n\n"

            "**How to read this comparison**\n\n"

            "- ✓ = Confirmed from the retrieved "
            "official bank page content or approved "
            "official product URL.\n"

            "- ? = Not confirmed from the retrieved "
            "official source. It does not mean the "
            "bank does not provide the service.\n\n"

            "This comparison uses only information "
            "retrieved from the banks' official "
            "public websites."
        )

    else:

        answer = (
            f"**NIB vs {competitor.name} — "
            f"{topic}**\n\n"

            f"### Nib International Bank\n"
            f"{nib_section}\n\n"

            f"### {competitor.name}\n"
            f"{competitor_section}\n\n"

            "**Comparison Note**\n\n"

            "This comparison is based only on "
            "information retrieved from the banks' "
            "official public websites."
        )

    return {
        "success": True,
        "answer": answer,
        "source_type":
            "bank_public_comparison",

        "sources":
            build_source_list(
                nib_pages,
                competitor_pages,
            ),

        "warnings": [],

        "retrieved_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }