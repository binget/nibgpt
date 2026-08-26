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
    maximum_pages: int = 2,
) -> list[dict]:
    question_terms = (
        normalize_terms(
            question
        )
    )

    urls = (
        discover_competitor_links(
            source=source,
            maximum_links=60,
        )
    )

    scored = []

    for url in urls:
        url_terms = (
            normalize_terms(
                url.replace(
                    "-",
                    " "
                )
            )
        )

        score = len(
            question_terms
            & url_terms
        )

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

    pages = []

    for _, url in scored[
        :maximum_pages
    ]:
        try:
            page = (
                fetch_competitor_page(
                    url=url,
                    source=source,
                )
            )

            if page.get("text"):
                pages.append(
                    page
                )

        except Exception:
            continue

    # Fallback to homepage.
    if not pages:
        pages.append(
            fetch_competitor_page(
                url=source.base_url,
                source=source,
            )
        )

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


def normalize_question(
    question: str,
) -> str:
    return " ".join(
        question.lower().split()
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