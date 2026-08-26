from datetime import (
    datetime,
    timezone,
)

import re

from app.ai.providers.factory import (
    get_ai_provider,
)

from app.ai.web_retriever import (
    fetch_discovered_pages,
    fetch_source_pages,
)

from app.ai.web_sources import (
    NIB_PUBLIC_SOURCE,
)


NIB_WEBSITE_PATHS = [
    "/",
    "/about-nib-bank/",
    "/executive-management/",
    "/internet-banking/",
    "/mobile-banking/",
    "/interest-free-banking/",
    "/branch-atms-pos/",
    "/investor-relations/",
]


WEB_SYSTEM_PROMPT = """
You are NIBGPT's Public Web Intelligence Agent
for NIB International Bank.

You answer questions using ONLY the public source
content supplied to you.

STRICT RULES:
- Never invent bank products, features, figures,
  locations, announcements or services.
- Never claim that website content is internal policy.
- Distinguish public website information from internal
  NIB International Bank information.
- Do not use model memory for bank-specific facts when
  retrieved source content is available.
- If the supplied sources do not answer the question,
  say that the available public sources were insufficient.
- Do not invent URLs.
- Give a clear and concise answer.
- Mention the relevant source names naturally.
- Do not repeat large portions of the website.
- Public information may change, so treat retrieved
  content as information available at retrieval time.
- Normally answer in 2 to 5 short paragraphs.
- Focus only on information relevant to the user's question.
- Do not summarize unrelated parts of the website.
- Do not repeat navigation menus, headers, footers, contact blocks,
  or unrelated website text.
- For direct factual questions such as names, titles, locations,
  dates, products, or services, answer only the requested fact first.
- If the source clearly contains the answer, do not provide unrelated
  website content.
- Never output corrupted page fragments, repeated tokens, navigation
  text, code fragments, or meaningless text.
- If the retrieved content appears corrupted or insufficient, say that
  the source could not be reliably interpreted.
- For leadership questions, identify only names and titles explicitly
  present in the retrieved official source.
- Do not infer reporting lines or positions.
- Preserve each name and official job title exactly as presented.
- Never combine a name from one record with a title from another record.
- If the user asks for the chief executive or CEO, do not include deputy
  chief executives unless explicitly requested.
- If the user asks for deputy chief executives, do not include the chief
  executive.
- If the user asks for district directors, use only the District Directors
  section.
- If the user asks for department directors, use only the Department
  Directors section.
- Do not mix Executive Management, Senior Management, District Directors,
  and Department Directors.
- Answer only the requested role or management group.
- If a name/title pairing is unclear, omit it rather than guessing.
- For product and service questions, mention only products or features
  explicitly found in the supplied official NIB website content.
- Do not invent eligibility criteria, pricing, fees, interest rates,
  limits, or terms unless they are explicitly present in the source.
- If multiple product variants are listed, summarize them clearly
  without omitting important distinctions.
""".strip()


MANAGEMENT_HEADINGS = (
    "Executive Management",
    "Senior Management",
    "District Directors",
    "Department Directors",
)


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


def normalize_phrase(
    text: str,
) -> str:
    return " ".join(
        text.lower().split()
    )

def detect_product_request(
    question: str,
) -> str | None:
    normalized = (
        " ".join(
            question.lower().split()
        )
    )

    product_groups = {
        "internet_banking": [
            "internet banking",
            "online banking",
        ],

        "mobile_banking": [
            "mobile banking",
            "mobile app",
            "digital banking",
        ],

        "interest_free_banking": [
            "interest free banking",
            "interest-free banking",
            "ifb",
        ],

        "deposit": [
            "deposit",
            "deposits",
            "saving",
            "savings",
            "current account",
            "fixed deposit",
        ],

        "loan": [
            "loan",
            "loans",
            "credit product",
            "credit products",
            "financing",
        ],

        "trade_service": [
            "trade finance",
            "trade service",
            "trade services",
            "letter of credit",
            "lc",
            "guarantee",
            "documentary collection",
        ],

        "forex": [
            "forex",
            "foreign exchange",
            "fx service",
            "currency exchange",
        ],

        "transfer": [
            "local transfer",
            "money transfer",
            "remittance",
            "transfer service",
        ],

        "atm_pos": [
            "atm",
            "pos",
            "point of sale",
        ],
    }

    for group, terms in (
        product_groups.items()
    ):
        if any(
            term in normalized
            for term in terms
        ):
            return group

    return None

def detect_management_request(
    question: str,
) -> str | None:
    normalized = normalize_phrase(
        question
    )

    # Most-specific phrases first.
    if any(
        term in normalized
        for term in (
            "deputy chief executive officer",
            "deputy chief executive officers",
            "deputy chief executive",
            "deputy chief executives",
            "deputy ceo",
            "deputy ceos",
            "deputy chief",
            "deputies",
        )
    ):
        return "deputy_chief"

    if any(
        term in normalized
        for term in (
            "chief executive officer",
            "chief executive",
            "ceo",
        )
    ):
        return "chief"

    if any(
        term in normalized
        for term in (
            "district director",
            "district directors",
        )
    ):
        return "district_directors"

    if any(
        term in normalized
        for term in (
            "department director",
            "department directors",
        )
    ):
        return "department_directors"

    if any(
        term in normalized
        for term in (
            "senior management",
            "senior manager",
            "senior managers",
        )
    ):
        return "senior_management"

    if "executive management" in normalized:
        return "executive_management"

    if any(
        term in normalized
        for term in (
            "director",
            "directors",
        )
    ):
        return "all_directors"

    return None


def _heading_key(
    line: str,
) -> str | None:
    normalized = normalize_phrase(
        line
    )

    for heading in MANAGEMENT_HEADINGS:
        if normalized == normalize_phrase(
            heading
        ):
            return heading

    return None


def split_management_sections(
    text: str,
) -> dict[str, str]:
    """
    Split the flattened Executive Management page by the
    four visible management headings.

    There can be duplicate heading labels in tab/navigation
    markup. We therefore keep the longest non-empty block for
    each heading instead of blindly using the first occurrence.
    """
    lines = [
        " ".join(
            line.split()
        )
        for line in text.splitlines()
        if line.strip()
    ]

    candidates: dict[
        str,
        list[str],
    ] = {
        heading: []
        for heading in MANAGEMENT_HEADINGS
    }

    occurrences: list[
        tuple[int, str]
    ] = []

    for index, line in enumerate(
        lines
    ):
        heading = _heading_key(
            line
        )

        if heading:
            occurrences.append(
                (
                    index,
                    heading,
                )
            )

    for occurrence_index, (
        line_index,
        heading,
    ) in enumerate(
        occurrences
    ):
        next_index = (
            occurrences[
                occurrence_index + 1
            ][0]
            if occurrence_index + 1
            < len(occurrences)
            else len(lines)
        )

        content_lines = lines[
            line_index + 1:
            next_index
        ]

        # Remove accidental repeated management headings.
        content_lines = [
            line
            for line in content_lines
            if _heading_key(line)
            is None
        ]

        content = "\n".join(
            content_lines
        ).strip()

        if content:
            candidates[
                heading
            ].append(
                content
            )

    sections = {}

    for heading, blocks in (
        candidates.items()
    ):
        if not blocks:
            continue

        # Tab navigation can create empty/short blocks.
        # The real panel is normally the longest block.
        sections[heading] = max(
            blocks,
            key=len,
        )

    return sections


def extract_role_records(
    section_text: str,
    requested_role: str,
    maximum_records: int = 20,
) -> str:
    """
    Extract tight name/title evidence for CEO/deputy questions.

    We do not use this for district/department director groups;
    those are already isolated by their management section.
    """
    lines = [
        " ".join(
            line.split()
        )
        for line in section_text.splitlines()
        if line.strip()
    ]

    if requested_role == "deputy_chief":
        aliases = (
            "deputy chief executive officer",
            "deputy chief executive",
            "deputy ceo",
            "deputy chief",
        )

    elif requested_role == "chief":
        aliases = (
            "chief executive officer",
            "chief executive",
            "ceo",
        )

    else:
        return section_text

    records = []
    used = set()

    for index, line in enumerate(
        lines
    ):
        lowered = line.lower()

        if not any(
            alias in lowered
            for alias in aliases
        ):
            continue

        if (
            requested_role
            == "deputy_chief"
            and "deputy"
            not in lowered
        ):
            continue

        if (
            requested_role
            == "chief"
            and "deputy"
            in lowered
        ):
            continue

        # Website cards commonly expose a name immediately
        # before or after its title. Keep a tight evidence
        # window and never include another role category.
        start = max(
            0,
            index - 1,
        )
        end = min(
            len(lines),
            index + 2,
        )

        block = lines[
            start:end
        ]

        # For a CEO request, remove neighbouring deputy lines.
        if requested_role == "chief":
            block = [
                item
                for item in block
                if "deputy chief"
                not in item.lower()
                and "deputy ceo"
                not in item.lower()
            ]

        # For deputy request, require the actual role line
        # in each returned block.
        if (
            requested_role
            == "deputy_chief"
            and not any(
                "deputy"
                in item.lower()
                for item in block
            )
        ):
            continue

        signature = tuple(
            block
        )

        if signature in used:
            continue

        used.add(
            signature
        )

        records.append(
            "\n".join(
                block
            )
        )

        if (
            len(records)
            >= maximum_records
        ):
            break

    return "\n\n".join(
        records
    )


def extract_management_evidence(
    question: str,
    page: dict,
) -> str:
    requested = (
        detect_management_request(
            question
        )
    )

    if not requested:
        return ""

    sections = (
        page.get("sections")
        or []
    )

    section_map = {}

    for section in sections:
        heading = (
            " ".join(
                (
                    section.get("heading")
                    or ""
                ).lower().split()
            )
        )

        content = (
            section.get("content")
            or ""
        ).strip()

        if (
            heading
            and content
        ):
            section_map[
                heading
            ] = content

    # ----------------------------------------------
    # District Directors
    # ----------------------------------------------

    if requested == "district_directors":
        return section_map.get(
            "district directors",
            "",
        )

    # ----------------------------------------------
    # Department Directors
    # ----------------------------------------------

    if requested == "department_directors":
        return section_map.get(
            "department directors",
            "",
        )

    # ----------------------------------------------
    # Senior Management
    # ----------------------------------------------

    if requested == "senior_management":
        return section_map.get(
            "senior management",
            "",
        )

    # ----------------------------------------------
    # Executive Management
    # ----------------------------------------------

    executive_text = (
        section_map.get(
            "executive management",
            "",
        )
    )

    if requested == "executive_management":
        return executive_text

    # CEO/deputy filtering can still use the
    # Executive Management panel only.
    if requested in {
        "chief",
        "deputy_chief",
    }:
        if not executive_text:
            return ""

        return extract_role_records(
            section_text=executive_text,
            requested_role=requested,
        )

    # ----------------------------------------------
    # Generic directors request
    # ----------------------------------------------

    if requested == "all_directors":
        district = (
            section_map.get(
                "district directors",
                "",
            )
        )

        department = (
            section_map.get(
                "department directors",
                "",
            )
        )

        blocks = []

        if district:
            blocks.append(
                "District Directors\n"
                + district
            )

        if department:
            blocks.append(
                "Department Directors\n"
                + department
            )

        return "\n\n".join(
            blocks
        )

    return ""


def extract_relevant_snippets(
    question: str,
    text: str,
    maximum_snippets: int = 8,
) -> list[str]:
    """
    General non-management fallback relevance extractor.
    """
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

    scored_lines = []

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

        if score > 0:
            scored_lines.append(
                (
                    score,
                    index,
                )
            )

    scored_lines.sort(
        key=lambda item:
            item[0],
        reverse=True,
    )

    snippets = []
    used_indexes = set()

    for _, index in scored_lines:
        start = max(
            0,
            index - 2,
        )

        end = min(
            len(lines),
            index + 3,
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

    return snippets


def select_relevant_content(
    question: str,
    pages: list[dict],
    maximum_characters: int = 12000,
) -> list[dict]:
    question_terms = (
        normalize_terms(
            question
        )
    )

    question_lower = (
        normalize_phrase(
            question
        )
    )

    management_request = (
        detect_management_request(
            question
        )
    )

    scored = []

    for page in pages:
        text = (
            page.get("text")
            or ""
        )

        if not text:
            continue

        title = (
            page.get("title")
            or ""
        ).lower()

        url = (
            page.get("url")
            or ""
        ).lower()

        text_terms = (
            normalize_terms(
                text[:30000]
            )
        )

        title_terms = (
            normalize_terms(
                title
            )
        )

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
            & text_terms
        )

        score += (
            len(
                question_terms
                & title_terms
            )
            * 6
        )

        score += (
            len(
                question_terms
                & url_terms
            )
            * 4
        )

        # Every management-group question belongs to the
        # Executive Management page shown on the NIB site.
        if management_request:
            if (
                "executive-management"
                in url
                or "executive management"
                in title
            ):
                score += 1000

        if (
            "internet banking"
            in question_lower
            and (
                "internet-banking"
                in url
                or "internet banking"
                in title
            )
        ):
            score += 100

        if (
            "mobile banking"
            in question_lower
            and (
                "mobile-banking"
                in url
                or "mobile banking"
                in title
            )
        ):
            score += 100

        if (
            (
                "interest free"
                in question_lower
                or "interest-free"
                in question_lower
            )
            and (
                "interest-free-banking"
                in url
                or "interest free"
                in title
                or "interest-free"
                in title
            )
        ):
            score += 100

        if (
            any(
                term in question_lower
                for term in (
                    "atm",
                    "pos",
                    "branch",
                    "branches",
                )
            )
            and "branch-atms-pos"
            in url
        ):
            score += 100

        if (
            any(
                term in question_lower
                for term in (
                    "investor",
                    "investors",
                    "shareholder",
                    "shareholders",
                )
            )
            and (
                "investor-relations"
                in url
                or "investor relations"
                in title
            )
        ):
            score += 100

        scored.append(
            (
                score,
                page,
            )
        )

    scored.sort(
        key=lambda item:
            item[0],
        reverse=True,
    )

    if not scored:
        return []

    score, page = (
        scored[0]
    )

    if score <= 0:
        return []

    text = ""

    if management_request:
        text = (
            extract_management_evidence(
                question=question,
                page=page,
            )
        )

    if not text:
        snippets = (
            extract_relevant_snippets(
                question=question,
                text=(
                    page.get(
                        "text"
                    )
                    or ""
                ),
            )
        )

        text = "\n\n".join(
            snippets
        )

    if not text:
        text = (
            page.get(
                "text",
                "",
            )
        )

    # Do not truncate management lists.
    if (
        not management_request
        and len(text)
        > maximum_characters
    ):
        text = (
            text[
                :maximum_characters
            ]
        )

    return [
        {
            "title":
                page.get(
                    "title"
                ),

            "url":
                page.get(
                    "url"
                ),

            "text":
                text,
        }
    ]

    

def get_nib_public_pages(
    question: str | None = None,
) -> list[dict]:

    normalized = (
        question.lower()
        if question
        else ""
    )

    management_request = (
        detect_management_request(
            question or ""
        )
    )

    if management_request:
        return fetch_source_pages(
            source=NIB_PUBLIC_SOURCE,
            paths=[
                "/executive-management/",
            ],
        )

    product_request = (
        detect_product_request(
            question or ""
        )
    )

    product_paths = {
        "internet_banking": [
            "/internet-banking/",
        ],

        "mobile_banking": [
            "/mobile-banking/",
        ],

        "interest_free_banking": [
            "/interest-free-banking/",
        ],

        "deposit": [
            "/deposit/",
        ],

        "loan": [
            "/types-of-loans/",
        ],

        "trade_service": [
            "/trade-service/",
        ],

        "forex": [
            "/forex-service/",
        ],

        "transfer": [
            "/local-transfer/",
            "/money-transfer/",
        ],

        "atm_pos": [
            "/branch-atms-pos/",
        ],
    }

    if (
        product_request
        and product_request
        in product_paths
    ):
        return fetch_source_pages(
            source=NIB_PUBLIC_SOURCE,
            paths=product_paths[
                product_request
            ],
        )

    try:
        discovered_pages = (
            fetch_discovered_pages(
                source=NIB_PUBLIC_SOURCE,
                maximum_pages=8,
            )
        )

        if discovered_pages:
            return discovered_pages

    except Exception:
        pass

    return fetch_source_pages(
        source=NIB_PUBLIC_SOURCE,
        paths=[
            "/",
            "/about-nib-bank/",
        ],
    )
    
def build_management_answer(
    question: str,
    selected: list[dict],
) -> str | None:
    requested = (
        detect_management_request(
            question
        )
    )

    if not requested:
        return None

    if not selected:
        return None

    text = (
        selected[0].get(
            "text"
        )
        or ""
    ).strip()

    if not text:
        return None

    labels = {
        "chief":
            "Chief Executive",
        "deputy_chief":
            "Deputy Chief Executives",
        "district_directors":
            "District Directors",
        "department_directors":
            "Department Directors",
        "senior_management":
            "Senior Management",
        "executive_management":
            "Executive Management",
        "all_directors":
            "Directors",
    }

    label = labels.get(
        requested,
        "Management",
    )

    return (
        f"**{label}**\n\n"
        f"{text}"
    )
    
    
def format_management_list(
    text: str,
) -> str:
    lines = [
        " ".join(
            line.split()
        )
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return ""

    formatted = []

    index = 0

    while index < len(lines):
        name = lines[index]

        # Most management cards appear as:
        #
        # Name
        # Department / Position
        # Director
        #
        # so group three consecutive lines.
        if index + 2 < len(lines):
            position = lines[index + 1]
            title = lines[index + 2]

            if (
                "director"
                in title.lower()
            ):
                formatted.append(
                    f"- **{name}** — "
                    f"{position} — "
                    f"{title}"
                )

                index += 3
                continue

        # Fallback: preserve any unmatched line.
        formatted.append(
            f"- {name}"
        )

        index += 1

    return "\n".join(
        formatted
    )


def answer_nib_website_question(
    question: str,
) -> dict:
    pages = get_nib_public_pages(
        question=question
    )

    selected = (
        select_relevant_content(
            question=question,
            pages=pages,
        )
    )

    if not selected:
        return {
            "success": False,
            "answer": (
                "I could not find enough "
                "approved NIB public website "
                "content to answer that question."
            ),
            "sources": [],
            "warnings": [],
            "retrieved_at": None,
        }

    retrieved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    # ==================================================
    # MANAGEMENT / LEADERSHIP
    #
    # IMPORTANT:
    # Do not send these lists to Ollama.
    # Return the verified extracted website content
    # directly.
    # ==================================================

    management_request = (
        detect_management_request(
            question
        )
    )

    if management_request:
        management_text = (
            selected[0].get(
                "text"
            )
            or ""
        ).strip()

        if not management_text:
            return {
                "success": False,
                "answer": (
                    "The official NIB website "
                    "was retrieved, but the "
                    "requested management section "
                    "could not be extracted."
                ),
                "sources": [],
                "warnings": [],
                "retrieved_at":
                    retrieved_at,
            }

        labels = {
            "chief":
                "Chief Executive",

            "deputy_chief":
                "Deputy Chief Executives",

            "district_directors":
                "District Directors",

            "department_directors":
                "Department Directors",

            "senior_management":
                "Senior Management",

            "executive_management":
                "Executive Management",

            "all_directors":
                "Directors",
        }

        label = labels.get(
            management_request,
            "Management",
        )

        # Remove internal extraction labels
        # before displaying them.
        internal_labels = [
            "CHIEF EXECUTIVE ONLY",
            "DEPUTY CHIEF EXECUTIVES ONLY",
            "DISTRICT DIRECTORS ONLY",
            "DEPARTMENT DIRECTORS ONLY",
            "SENIOR MANAGEMENT ONLY",
            "EXECUTIVE MANAGEMENT ONLY",
        ]

        for internal_label in (
            internal_labels
        ):
            management_text = (
                management_text.replace(
                    internal_label,
                    "",
                )
            )

        management_text = (
            management_text.strip()
        )
        
        if management_request in {
            "district_directors",
            "department_directors",
        }:
            management_text = (
                format_management_list(
                    management_text
                )
            )

        return {
            "success": True,

            "answer": (
                f"**{label}**\n\n"
                f"{management_text}"
            ),

            "source_type":
                "nib_public_web",

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
                        page.get(
                            "url"
                        ),

                    "trust_level":
                        "official",
                }
                for page in selected
            ],
        }

    # ==================================================
    # NORMAL WEB QUESTIONS
    #
    # Only these questions use Ollama.
    # ==================================================

    source_blocks = []

    for index, page in enumerate(
        selected,
        start=1,
    ):
        source_blocks.append(
            (
                f"SOURCE {index}\n"
                f"Title: "
                f"{page.get('title')}\n"
                f"URL: "
                f"{page.get('url')}\n"
                f"Content:\n"
                f"{page.get('text', '')}"
            )
        )

    provider = (
        get_ai_provider()
    )

    prompt = (
        "User question:\n"
        f"{question}\n\n"
        "Approved public website content:\n\n"
        + "\n\n".join(
            source_blocks
        )
    )

    answer = provider.generate(
        prompt=prompt,
        system_prompt=(
            WEB_SYSTEM_PROMPT
        ),
    )

    return {
        "success": True,

        "answer":
            answer,

        "source_type":
            "nib_public_web",

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
                    page.get(
                        "url"
                    ),

                "trust_level":
                    "official",
            }
            for page in selected
        ],
    }