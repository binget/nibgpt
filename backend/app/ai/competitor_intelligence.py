from datetime import (
    datetime,
    timezone,
)

from app.ai.competitor_sources import (
    COMPETITOR_SOURCES,
)

import re

from app.ai.providers.factory import (
    get_ai_provider,
)

from app.ai.competitor_retriever import (
    discover_competitor_links,
    fetch_competitor_page,
)

from urllib.parse import (
    urljoin,
)

from app.ai.competitor_seed_paths import (
    COMPETITOR_SEED_PATHS,
)


COMPETITOR_SYSTEM_PROMPT = """
You are NIBGPT's Competitor Intelligence Agent.

Use ONLY the supplied official public competitor
website content.

Rules:
- Never invent products, prices, rates, branches,
  services, eligibility rules or features.
- Clearly identify which bank the information belongs to.
- Do not claim public website information is internal data.
- For comparisons, compare only facts present in the
  supplied sources.
- If information is missing, say so.
- Keep answers professional and concise.
- Answer ONLY the user's actual question.
- Ignore unrelated website footer, security, vulnerability disclosure,
  privacy, legal, cookie, navigation, and corporate boilerplate content.
- If the question is about digital banking, discuss only digital banking
  products and features explicitly supported by the supplied evidence.
- Never answer a digital-banking question with unrelated security or
  vulnerability-disclosure information.
- Do not infer features that are not explicitly present.
- Answer in at most 6 concise bullets unless the user asks for detail.
- Do not repeat the source material.
- Do not describe unrelated website navigation items as banking services.
- For a product/service question, list only clearly supported services or features.
- Do not include generic navigation actions such as "Open an Account"
  unless they directly answer the user's question.
- Use ONLY products and services explicitly present in the supplied
  Relevant Content blocks.
- Do not use product names found only in menus, navigation, headers,
  footers, sidebars, or unrelated page sections.
- Every product mentioned in the answer must be supported by one of
  the supplied source pages.
- Do not add related products from memory.
- For a simple product/service question, answer in no more than
  4 concise bullets.
""".strip()

def get_seed_urls(
    source,
    product_type: str | None,
) -> list[str]:
    if not product_type:
        return []

    bank_paths = (
        COMPETITOR_SEED_PATHS.get(
            source.key,
            {}
        )
    )

    paths = (
        bank_paths.get(
            product_type,
            []
        )
    )

    return [
        urljoin(
            source.base_url,
            path,
        )
        for path in paths
    ]

def normalize_terms(
    text: str,
) -> set[str]:
    return {
        word
        for word in re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
        if len(word) >= 3
    }


def select_competitor_pages(
    question: str,
    source,
    maximum_pages: int = 3,
) -> list[dict]:
    question_terms = (
        normalize_terms(
            question
        )
    )

    product_type = (
        detect_competitor_product_request(
            question
        )
    )

    topic_keywords = (
        get_topic_keywords(
            question
        )
    )

    page_limit = (
        4
        if product_type == "loan"
        else maximum_pages
    )

    seed_urls = (
        get_seed_urls(
            source=source,
            product_type=product_type,
        )
    )

    pages = []
    seen_urls = set()

    # ==================================================
    # 1. Fetch approved seed URLs first
    # ==================================================

    for url in seed_urls:
        if len(pages) >= page_limit:
            break

        try:
            page = fetch_competitor_page(
                url=url,
                source=source,
            )

            text = (
                page.get("text")
                or ""
            )

            if len(text) < 80:
                continue

            final_url = (
                page.get("url")
                or url
            )

            if final_url in seen_urls:
                continue

            seen_urls.add(
                final_url
            )

            pages.append(
                page
            )

        except Exception as error:
            print(
                "SEED FETCH WARNING:",
                url,
                str(error),
            )

    # ==================================================
    # 2. Discover additional URLs only if needed
    # ==================================================

    if (
        len(pages) < page_limit
        and not seed_urls
    ):
        urls = (
            discover_competitor_links(
                source=source,
                maximum_links=150,
            )
        )

        scored = []

        for url in urls:
            if url in seen_urls:
                continue

            normalized_url = (
                url.lower()
                .replace("-", " ")
                .replace("_", " ")
            )

            url_terms = (
                normalize_terms(
                    normalized_url
                )
            )

            score = len(
                question_terms
                & url_terms
            )

            for keyword in topic_keywords:
                normalized_keyword = (
                    keyword.lower()
                    .replace("-", " ")
                    .replace("_", " ")
                )

                if (
                    normalized_keyword
                    in normalized_url
                ):
                    score += 15

            if product_type == "loan":
                lowered_url = (
                    url.lower()
                )

                if (
                    "/credit/"
                    in lowered_url
                ):
                    score += 40

                if (
                    "/products/loan"
                    in lowered_url
                ):
                    score += 40

                loan_unrelated = (
                    "/deposit",
                    "/trade-services",
                    "/diaspora",
                    "/announcement",
                    "/news",
                    "/cbe-resources/",
                    "/cbe-noor/",
                    "/cbenoor-",
                    "/noor-",
                )

                if any(
                    term in lowered_url
                    for term in loan_unrelated
                ):
                    score -= 100

            unrelated_terms = (
                "/about-us/",
                "/career",
                "/vacancy",
                "/news",
                "/contact",
                "/board",
                "/management",
                "/privacy",
                "/security",
            )

            if any(
                term in url.lower()
                for term in unrelated_terms
            ):
                score -= 50

            scored.append(
                (
                    score,
                    url,
                )
            )

        scored.sort(
            key=lambda item:
                item[0],
            reverse=True,
        )

        for score, url in scored:
            if len(pages) >= page_limit:
                break

            if score <= 0:
                continue

            try:
                page = (
                    fetch_competitor_page(
                        url=url,
                        source=source,
                    )
                )

                text = (
                    page.get("text")
                    or ""
                )

                if len(text) < 80:
                    continue

                final_url = (
                    page.get("url")
                    or url
                )

                if final_url in seen_urls:
                    continue

                seen_urls.add(
                    final_url
                )

                pages.append(
                    page
                )

            except Exception:
                continue

    # ==================================================
    # 3. Final fallback
    # ==================================================

    if not pages:
        try:
            page = (
                fetch_competitor_page(
                    url=source.base_url,
                    source=source,
                )
            )

            if page.get("text"):
                pages.append(
                    page
                )

        except Exception:
            pass

    return pages

def extract_relevant_competitor_snippets(
    question: str,
    text: str,
    maximum_snippets: int = 4,
) -> str:
    question_terms = (
        normalize_terms(
            question
        )
    )

    lines = [
        " ".join(
            line.split()
        )
        for line in text.splitlines()
        if line.strip()
    ]

    scored = []

    for index, line in enumerate(
        lines
    ):
        line_terms = (
            normalize_terms(
                line
            )
        )

        score = len(
            question_terms
            & line_terms
        )

        lowered = (
            line.lower()
        )

        # ------------------------------------------
        # Digital banking relevance
        # ------------------------------------------

        if any(
            term in question.lower()
            for term in (
                "digital banking",
                "mobile banking",
                "internet banking",
                "online banking",
            )
        ):
            if any(
                term in lowered
                for term in (
                    "digital",
                    "mobile",
                    "internet",
                    "banking",
                    "cbe birr",
                    "ethio direct",
                    "wallet",
                    "transfer",
                    "payment",
                    "airtime",
                )
            ):
                score += 10

        # ------------------------------------------
        # Loan relevance
        # ------------------------------------------

        if (
            "loan" in question.lower()
            or "loans" in question.lower()
        ):
            if any(
                term in lowered
                for term in (
                    "loan",
                    "credit",
                    "financing",
                    "borrow",
                )
            ):
                score += 10

        # ------------------------------------------
        # Deposit relevance
        # ------------------------------------------

        if (
            "deposit" in question.lower()
            or "saving" in question.lower()
        ):
            if any(
                term in lowered
                for term in (
                    "deposit",
                    "saving",
                    "current account",
                    "fixed",
                    "account",
                )
            ):
                score += 10

        # ------------------------------------------
        # Ignore obvious unrelated website content
        # ------------------------------------------

        if any(
            term in lowered
            for term in (
                "vulnerability disclosure",
                "responsible disclosure",
                "privacy policy",
                "cookie policy",
                "copyright",
                "terms and conditions",
                "security vulnerability",
            )
        ):
            score -= 100

        if score > 0:
            scored.append(
                (
                    score,
                    index,
                )
            )

    scored.sort(
        key=lambda item:
            item[0],
        reverse=True,
    )

    snippets = []
    used_indexes = set()

    for _, index in scored:
        start = max(
            0,
            index - 2,
        )

        end = min(
            len(lines),
            index + 4,
        )

        block_indexes = tuple(
            range(
                start,
                end,
            )
        )

        if any(
            item in used_indexes
            for item in block_indexes
        ):
            continue

        snippet = "\n".join(
            lines[start:end]
        )

        snippets.append(
            snippet
        )

        used_indexes.update(
            block_indexes
        )

        if (
            len(snippets)
            >= maximum_snippets
        ):
            break

    return "\n\n".join(
        snippets
    )

def answer_competitor_question(
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
            "answer":
                "No approved competitor was identified.",
            "sources": [],
        }

    all_pages = []

    for competitor in competitors:
        pages = (
            select_competitor_pages(
                question=question,
                source=competitor,
            )
        )

        all_pages.extend(
            pages
        )

    evidence = []

    for index, page in enumerate(
        all_pages,
        start=1,
    ):
        full_text = (
            page.get("text")
            or ""
        )

        text = (
            extract_relevant_competitor_snippets(
                question=question,
                text=full_text,
            )
        )
        
        # Keep competitor evidence small enough
        # for fast local-model generation.
        if len(text) > 700:
            text = text[:700]

        # Fallback only if relevance extraction
        # finds absolutely nothing.
        if not text:
            text = (
                full_text[:1800]
            )

        evidence.append(
            (
                f"SOURCE {index}\n"
                f"Bank: {page['bank_name']}\n"
                f"Title: {page.get('title')}\n"
                f"URL: {page['url']}\n"
                f"Relevant Content:\n"
                f"{text}"
            )
        )

        evidence.append(
            (
                f"SOURCE {index}\n"
                f"Bank: {page['bank_name']}\n"
                f"Title: {page.get('title')}\n"
                f"URL: {page['url']}\n"
                f"Content:\n{text}"
            )
        )
        
        # ==================================================
    # Simple competitor product/service questions
    # bypass Ollama completely.
    # ==================================================

    if len(competitors) == 1:
        direct_answer = (
            build_competitor_product_answer(
                question=question,
                pages=all_pages,
            )
        )

        if direct_answer:
            retrieved_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            return {
                "success": True,

                "answer":
                    direct_answer,

                "source_type":
                    "competitor_public_web",

                "retrieved_at":
                    retrieved_at,

                "warnings": [],

                "sources": [
                    {
                        "title":
                            page.get(
                                "title"
                            ),

                        "url":
                            page["url"],

                        "bank_name":
                            page["bank_name"],

                        "trust_level":
                            "official",
                    }
                    for page in all_pages
                ],
            }

    provider = (
        get_ai_provider()
    )

    prompt = (
        "Question:\n"
        f"{question}\n\n"
        "Approved competitor sources:\n\n"
        + "\n\n".join(
            evidence
        )
    )

    answer = provider.generate(
        prompt=prompt,
        system_prompt=(
            COMPETITOR_SYSTEM_PROMPT
        ),
    )

    retrieved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    return {
        "success": True,
        "answer": answer,
        "source_type":
            "competitor_public_web",
        "retrieved_at":
            retrieved_at,
        "warnings": [],
        "sources": [
            {
                "title":
                    page.get("title"),
                "url":
                    page["url"],
                "bank_name":
                    page["bank_name"],
                "trust_level":
                    "official",
            }
            for page in all_pages
        ],
    }

def get_topic_keywords(
    question: str,
) -> tuple[str, ...]:
    product_type = (
        detect_competitor_product_request(
            question
        )
    )

    mapping = {
        "digital_banking": (
            "digital",
            "mobile",
            "internet",
            "wallet",
            "ways-of-banking",
            "cbe-birr",
            "ethio-direct",
        ),

        "loan": (
            "loan",
            "loans",
            "credit",
            "financing",
            "mortgage",
            "overdraft",
            "term-loan",
            "term loan",
            "vehicle",
            "agriculture",
            "construction",
            "merchandise",
        ),

        "deposit": (
            "deposit",
            "saving",
            "savings",
            "current",
            "fixed",
            "account",
        ),

        "trade": (
            "trade",
            "letter-of-credit",
            "lc",
            "guarantee",
            "documentary",
            "import",
            "export",
        ),

        "interest_free": (
            "interest-free",
            "ifb",
            "noor",
            "sharia",
        ),

        "forex": (
            "forex",
            "foreign-exchange",
            "currency",
            "remittance",
        ),
    }

    return mapping.get(
        product_type,
        (),
    )
    
def normalize_question(
    question: str,
) -> str:
    return " ".join(
        question.lower().split()
    )

def detect_competitor_product_request(
    question: str,
) -> str | None:
    normalized = (
        " ".join(
            question.lower().split()
        )
    )

    groups = {
        "digital_banking": [
            "digital banking",
            "mobile banking",
            "internet banking",
            "online banking",
            "wallet",
        ],

        "loan": [
            "loan",
            "loans",
            "credit",
            "financing",
        ],

        "deposit": [
            "deposit",
            "deposits",
            "saving",
            "savings",
            "current account",
            "fixed deposit",
        ],

        "trade": [
            "trade finance",
            "trade service",
            "trade services",
            "letter of credit",
            "lc",
            "guarantee",
        ],

        "interest_free": [
            "interest free",
            "interest-free",
            "ifb",
            "islamic banking",
        ],

        "forex": [
            "forex",
            "foreign exchange",
            "currency exchange",
        ],
    }

    for group, terms in groups.items():
        if any(
            term in normalized
            for term in terms
        ):
            return group

    return None

def extract_competitor_product_facts(
    question: str,
    pages: list[dict],
) -> list[str]:
    product_type = (
        detect_competitor_product_request(
            question
        )
    )

    if not product_type:
        return []

    keywords = {
        "digital_banking": [
            "mobile banking",
            "internet banking",
            "digital banking",
            "wallet",
            "cbe birr",
            "ethio direct",
            "mobile app",
            "mobile application",
            "transfer",
            "payment",
            "airtime",
        ],

        "loan": [
            "loan",
            "credit",
            "financing",
        ],

        "deposit": [
            "deposit",
            "saving",
            "savings",
            "current account",
            "fixed deposit",
        ],

        "trade": [
            "trade",
            "letter of credit",
            "documentary",
            "guarantee",
            "lc",
        ],

        "interest_free": [
            "interest free",
            "interest-free",
            "ifb",
            "noor",
            "sharia",
        ],

        "forex": [
            "forex",
            "foreign exchange",
            "currency",
        ],
    }

    wanted = keywords.get(
        product_type,
        [],
    )

    blocked = (
        "vulnerability",
        "privacy policy",
        "cookie",
        "copyright",
        "terms and conditions",
        "security disclosure",
        "responsible disclosure",
        "useful links",
        "contact us",
    )

    facts = []
    seen = set()

    for page in pages:
        text = (
            page.get("text")
            or ""
        )

        lines = [
            " ".join(
                line.split()
            )
            for line in text.splitlines()
            if line.strip()
        ]

        for line in lines:
            lowered = (
                line.lower()
            )

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

            # Ignore very long navigation/footer lines.
            if len(line) > 250:
                continue

            key = lowered

            if key in seen:
                continue

            seen.add(
                key
            )

            facts.append(
                line
            )

            if len(facts) >= 12:
                return facts

    return facts

def build_competitor_product_answer(
    question: str,
    pages: list[dict],
) -> str | None:
    facts = (
        extract_competitor_product_facts(
            question=question,
            pages=pages,
        )
    )

    if not facts:
        return None

    bank_name = (
        pages[0].get(
            "bank_name"
        )
        if pages
        else "The bank"
    )

    product_type = (
        detect_competitor_product_request(
            question
        )
    )

    labels = {
        "digital_banking":
            "Digital Banking Services",

        "loan":
            "Loan and Financing Services",

        "deposit":
            "Deposit Products",

        "trade":
            "Trade Finance Services",

        "interest_free":
            "Interest-Free Banking Services",

        "forex":
            "Foreign Exchange Services",
    }

    heading = labels.get(
        product_type,
        "Public Banking Services",
    )

    bullets = "\n".join(
        f"- {fact}"
        for fact in facts
    )

    return (
        f"**{bank_name} — {heading}**\n\n"
        f"{bullets}"
    )

def detect_competitors(
    question: str,
) -> list:
    normalized = (
        normalize_question(
            question
        )
    )

    matched = []

    for source in (
        COMPETITOR_SOURCES.values()
    ):
        if any(
            alias in normalized
            for alias in source.aliases
        ):
            matched.append(
                source
            )

    return matched


def is_competitor_question(
    question: str,
) -> bool:
    return bool(
        detect_competitors(
            question
        )
    )