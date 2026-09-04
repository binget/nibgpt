import re
from collections import Counter


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at",
    "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or",
    "that", "the", "this", "to", "was",
    "what", "when", "where", "which", "who",
    "with", "does", "do", "about", "say",
}


NUMBERED_LINE_PATTERN = re.compile(
    r"^[\s|,;:\-]*"
    r"(?P<number>\d+(?:\.\d+){0,4})"
    r"\.?"
    r"\s+"
    r"(?P<title>.+?)"
    r"\s*$"
)


ROLE_HINTS = (
    "board",
    "president",
    "vice president",
    "v/p",
    "department",
    "director",
    "committee",
    "division",
    "office",
    "unit",
    "management",
)

CLAUSE_START_WORDS = (
    "ensure",
    "ensures",
    "identify",
    "identifies",
    "appoint",
    "appoints",
    "approve",
    "approves",
    "review",
    "reviews",
    "monitor",
    "monitors",
    "conduct",
    "conducts",
    "decide",
    "decides",
    "undertake",
    "undertakes",
    "provide",
    "provides",
    "maintain",
    "maintains",
    "prepare",
    "prepares",
    "submit",
    "submits",
    "report",
    "reports",
    "enforce",
    "enforces",
    "take",
    "takes",
    "perform",
    "performs",
    "verify",
    "verifies",
    "establish",
    "establishes",
    "develop",
    "develops",
    "implement",
    "implements",
)

CHAPTER_PATTERN = re.compile(
    r"^\s*CHAPTER\s+"
    r"(?:"
    r"[A-Z]+"
    r"|[IVXLCDM]+"
    r"|\d+"
    r")"
    r"\s*$",
    re.IGNORECASE,
)


def is_chapter_heading(
    line: str,
) -> bool:
    if not line:
        return False

    cleaned = normalize_line(
        line
    )

    return bool(
        CHAPTER_PATTERN.match(
            cleaned
        )
    )


def looks_like_heading_title(
    title: str,
) -> bool:

    title = normalize_line(
        title
    )

    if not title:
        return False

    # Real headings should normally be relatively short.
    if len(title) > 160:
        return False

    words = re.findall(
        r"[A-Za-z0-9/&'-]+",
        title,
    )

    if not words:
        return False

    if len(words) > 18:
        return False

    lowered = title.lower()

    first_word = (
        words[0].lower()
        if words
        else ""
    )

    # These usually indicate a numbered clause/action,
    # not a document section heading.
    if first_word in CLAUSE_START_WORDS:
        return False

    # Sentences containing these forms are usually
    # requirements or obligations.
    sentence_markers = (
        " shall ",
        " should ",
        " must ",
        " will ",
        " may ",
        " is required to ",
        " are required to ",
    )

    if any(
        marker in f" {lowered} "
        for marker in sentence_markers
    ):
        return False

    # Long sentence ending in punctuation is probably
    # content rather than a heading.
    if (
        len(words) > 8
        and title.endswith(
            (
                ".",
                ";",
                ",",
            )
        )
    ):
        return False

    return True


def tokenize(
    text: str,
) -> list[str]:

    words = re.findall(
        r"[a-zA-Z0-9]+",
        (text or "").lower(),
    )

    return [
        word
        for word in words
        if (
            len(word) > 2
            and word not in STOP_WORDS
        )
    ]


def normalize_line(
    line: str,
) -> str:

    line = (
        line
        or ""
    )

    line = line.replace(
        "\t",
        " ",
    )

    line = re.sub(
        r"\s+",
        " ",
        line,
    )

    return line.strip()


def clean_numbered_prefix(
    line: str,
) -> str:

    return re.sub(
        r"^[|,;:\-\s]+",
        "",
        normalize_line(line),
    )


def parse_numbered_line(
    line: str,
) -> dict | None:

    cleaned = clean_numbered_prefix(
        line
    )

    if not cleaned:
        return None

    match = NUMBERED_LINE_PATTERN.match(
        cleaned
    )

    if not match:
        return None

    number = (
        match.group("number")
        .strip()
        .rstrip(".")
    )

    title = (
        match.group("title")
        .strip()
    )

    if not title:
        return None

    return {
        "number": number,
        "title": title,
        "raw": cleaned,
        "depth": len(
            number.split(".")
        ),
    }


def looks_like_toc_page(
    text: str,
) -> bool:

    normalized = (
        text
        or ""
    ).strip()

    if not normalized:
        return False

    lowered = normalized.lower()

    # Strongest signal:
    # explicit table-of-contents heading.
    if (
        "table of contents" in lowered
        or re.search(
            r"^\s*contents\s*$",
            lowered,
            flags=re.MULTILINE,
        )
    ):
        return True

    lines = [
        normalize_line(line)
        for line in normalized.splitlines()
        if normalize_line(line)
    ]

    if not lines:
        return False

    dotted_entries = 0
    toc_like_entries = 0

    for line in lines:

        # Typical TOC dotted leader:
        #
        # 8.2 Credit Monitoring ............ 39
        # 13.4 Revision of Policy .......... 47
        if re.search(
            r"\.{3,}",
            line,
        ):
            dotted_entries += 1

            if re.match(
                r"^\s*\d+(?:\.\d+){0,4}\.?\s+",
                line,
            ):
                toc_like_entries += 1

    # A real contents page normally contains
    # several dotted-leader entries.
    #
    # Do NOT classify a page as TOC merely
    # because it has many numbered clauses.
    if (
        dotted_entries >= 3
        and toc_like_entries >= 2
    ):
        return True

    return False


def is_probable_footer_or_header(
    line: str,
) -> bool:

    normalized = (
        normalize_line(line)
        .lower()
    )

    if not normalized:
        return True

    # Page markers.
    if re.search(
        r"^page\s*\|?\s*\d+\s*$",
        normalized,
    ):
        return True

    if re.search(
        r"^page\s+\d+\s*$",
        normalized,
    ):
        return True

    # Common OCR variation:
    # pade| 4
    if re.search(
        r"^pa(?:ge|de)\s*\|?\s*\d+\s*$",
        normalized,
    ):
        return True

    # Standalone approval stamp/header.
    #
    # IMPORTANT:
    # Do NOT reject every line containing
    # "Board of Directors", because legitimate
    # policy clauses may say:
    #
    # "report to the Board of Directors."
    if (
        "approved by" in normalized
        and len(normalized) < 80
    ):
        return True

    return False

def is_probable_ocr_noise(
    line: str,
) -> bool:

    normalized = normalize_line(
        line
    )

    if not normalized:
        return True

    lowered = normalized.lower()

    # Known page-number OCR variants.
    if re.search(
        r"^pa(?:ge|de)\s*\|?\s*\d+\s*$",
        lowered,
    ):
        return True

    # Lines consisting mostly of OCR punctuation.
    alphanumeric_count = len(
        re.findall(
            r"[a-zA-Z0-9]",
            normalized,
        )
    )

    if (
        len(normalized) <= 12
        and alphanumeric_count <= 2
    ):
        return True

    return False


def is_role_heading(
    number: str,
    title: str,
    current_major: str | None,
) -> bool:

    parts = number.split(".")

    # Responsibility owners normally look like:
    # 5.1
    # 5.2
    # 5.3
    # 5.4
    # 5.5
    if len(parts) != 2:
        return False

    if (
        current_major
        and parts[0] != current_major
    ):
        return False

    normalized_title = (
        title
        or ""
    ).lower()

    if any(
        hint in normalized_title
        for hint in ROLE_HINTS
    ):
        return True

    # "The President shall"
    # "Planning and Monitoring Department shall"
    if " shall" in normalized_title:
        return True

    return False

def is_subsection_heading(
    number: str,
    title: str,
    current_major: str | None,
) -> bool:

    parts = (
        number
        .strip()
        .split(".")
    )

    # Generic subsection:
    #
    # 1.1 Purpose
    # 1.2 Scope
    # 3.1 Credit Products
    # 8.2 Credit Monitoring
    # 13.3 Violation of the Policy
    if len(parts) != 2:
        return False

    if not all(
        part.isdigit()
        for part in parts
    ):
        return False

    if current_major:

        if parts[0] != str(
            current_major
        ):
            return False

    # Organizational responsibility headings should
    # always be preserved.
    if is_role_heading(
        number=number,
        title=title,
        current_major=current_major,
    ):
        return True

    return looks_like_heading_title(
        title
    )

def is_major_heading(
    numbered: dict,
    current_major: str | None = None,
) -> bool:

    if not numbered:
        return False

    if numbered.get("depth") != 1:
        return False

    number = (
        numbered.get("number")
        or ""
    )

    title = (
        numbered.get("title")
        or ""
    )

    if not number.isdigit():
        return False

    if not looks_like_heading_title(
        title
    ):
        return False

    candidate = int(number)

    # Reject implausible OCR numbers such as:
    # 71, 104, 1122
    #
    # Major policy chapters are normally
    # small sequential integers.
    if candidate > 50:
        return False

    if current_major and current_major.isdigit():

        current = int(
            current_major
        )

        # Same or previous number cannot
        # start a new major section.
        if candidate <= current:
            return False

        # Major sections should normally
        # progress sequentially.
        #
        # This prevents acronym/list rows such as
        # 4 -> 7 -> 8 from becoming chapters.
        if candidate > current + 1:
            return False

    return True


def repair_ocr_clause_number(
    number: str,
    current_role_number: str | None,
) -> str:

    if not current_role_number:
        return number

    role_parts = (
        current_role_number.split(".")
    )

    if len(role_parts) != 2:
        return number

    expected_prefix = (
        f"{role_parts[0]}."
        f"{role_parts[1]}."
    )

    # Already correct:
    # 5.3.1
    if number.startswith(
        expected_prefix
    ):
        return number

    # OCR frequently removes the decimal:
    # 5.3.1 -> 53.1
    #
    # Current role = 5.3
    # OCR number   = 53.1
    collapsed_prefix = (
        f"{role_parts[0]}"
        f"{role_parts[1]}."
    )

    if number.startswith(
        collapsed_prefix
    ):
        suffix = number[
            len(collapsed_prefix):
        ]

        if suffix.isdigit():
            return (
                f"{current_role_number}."
                f"{suffix}"
            )

    return number


def looks_like_clause(
    numbered: dict,
    current_role_number: str | None,
) -> bool:

    if not current_role_number:
        return False

    repaired = (
        repair_ocr_clause_number(
            numbered["number"],
            current_role_number,
        )
    )

    return repaired.startswith(
        f"{current_role_number}."
    )


def create_section(
    section_number: str | None,
    section_title: str,
    parent_section_number: str | None,
    parent_section_title: str | None,
    page_number: int | None,
) -> dict:

    return {
        "section_number":
            section_number,

        "section_title":
            section_title,

        "parent_section_number":
            parent_section_number,

        "parent_section_title":
            parent_section_title,

        "start_page":
            page_number,

        "end_page":
            page_number,

        "lines": [],
    }


def extract_sections(
    pages: list[dict],
) -> list[dict]:

    sections = []

    current_major_number = None
    current_major_title = None
    chapter_heading_seen = False

    current_role_number = None
    current_role_title = None

    current_section = None

    for page in pages:

        page_number = page.get(
            "page_number"
        )

        page_text = (
            page.get("text")
            or ""
        ).strip()

        if not page_text:
            continue

        # The TOC is useful to a human, but dangerous
        # for section extraction because it duplicates
        # every heading before the real document body.
        if looks_like_toc_page(
            page_text
        ):
            print(
                "DEBUG SKIP TOC PAGE:",
                page_number,
            )
            continue

        lines = [
            normalize_line(line)
            for line in page_text.splitlines()
            if normalize_line(line)
        ]

        for line in lines:

            if is_probable_footer_or_header(
                line
            ):
                continue
            
            if is_probable_ocr_noise(
                line
            ):
                continue
            
            if is_chapter_heading(
                line
            ):
                chapter_heading_seen = True
                continue

            numbered = (
                parse_numbered_line(
                    line
                )
            )

            # -----------------------------------------
            # Major section
            # -----------------------------------------

            if (
                numbered
                and numbered.get("depth") == 1
                and (
                    chapter_heading_seen
                    or (
                        current_major_number is None
                        and looks_like_heading_title(
                            numbered["title"]
                        )
                    )
                )
            ):
                number = numbered["number"]
                title = numbered["title"]

                # Basic OCR safety.
                if (
                    number.isdigit()
                    and int(number) <= 50
                    and looks_like_heading_title(
                        title
                    )
                ):

                    current_major_number = number
                    current_major_title = title

                    current_role_number = None
                    current_role_title = None

                    current_section = {
                        "section_number": number,
                        "section_title": title,
                        "parent_section_number": None,
                        "parent_section_title": None,
                        "start_page": page_number,
                        "end_page": page_number,
                        "lines": [
                            f"{number}. {title}"
                        ],
                    }

                    sections.append(
                        current_section
                    )

                    chapter_heading_seen = False
                    continue

            # -----------------------------------------
            # Role / subsection heading
            # -----------------------------------------

            if (
                    numbered
                    and is_subsection_heading(
                        number=(
                            numbered[
                                "number"
                            ]
                        ),
                        title=(
                            numbered[
                                "title"
                            ]
                        ),
                        current_major=(
                            current_major_number
                        ),
                    )
                ):

                current_role_number = (
                    numbered["number"]
                )

                current_role_title = (
                    numbered["title"]
                )

                current_section = (
                    create_section(
                        section_number=(
                            current_role_number
                        ),
                        section_title=(
                            current_role_title
                        ),
                        parent_section_number=(
                            current_major_number
                        ),
                        parent_section_title=(
                            current_major_title
                        ),
                        page_number=page_number,
                    )
                )

                current_section[
                    "lines"
                ].append(
                    numbered["raw"]
                )

                sections.append(
                    current_section
                )

                continue

            # -----------------------------------------
            # Clause belonging to current role
            # -----------------------------------------

            if (
                numbered
                and looks_like_clause(
                    numbered=numbered,
                    current_role_number=(
                        current_role_number
                    ),
                )
            ):

                repaired_number = (
                    repair_ocr_clause_number(
                        number=(
                            numbered[
                                "number"
                            ]
                        ),
                        current_role_number=(
                            current_role_number
                        ),
                    )
                )

                clause_line = (
                    f"{repaired_number}. "
                    f"{numbered['title']}"
                )

                if current_section:

                    current_section[
                        "lines"
                    ].append(
                        clause_line
                    )

                    current_section[
                        "end_page"
                    ] = page_number

                continue

            # -----------------------------------------
            # Ordinary continuation line
            # -----------------------------------------

            if current_section is None:

                current_section = (
                    create_section(
                        section_number=None,
                        section_title=(
                            "Document Introduction"
                        ),
                        parent_section_number=None,
                        parent_section_title=None,
                        page_number=page_number,
                    )
                )

                sections.append(
                    current_section
                )

            current_section[
                "lines"
            ].append(
                line
            )

            current_section[
                "end_page"
            ] = page_number

    result = []

    for index, section in enumerate(
        sections,
        start=1,
    ):

        content = "\n".join(
            section["lines"]
        ).strip()

        if not content:
            continue

        result.append(
            {
                "section_id":
                    index,

                "section_number":
                    section[
                        "section_number"
                    ],

                "section_title":
                    section[
                        "section_title"
                    ],

                "parent_section_number":
                    section[
                        "parent_section_number"
                    ],

                "parent_section_title":
                    section[
                        "parent_section_title"
                    ],

                "start_page":
                    section[
                        "start_page"
                    ],

                "end_page":
                    section[
                        "end_page"
                    ],

                "content":
                    content,
            }
        )

    return result


def chunk_large_section(
    section: dict,
    chunk_size: int = 3500,
) -> list[dict]:

    content = (
        section.get("content")
        or ""
    ).strip()

    if not content:
        return []

    if len(content) <= chunk_size:
        return [
            {
                **section,
                "chunk_no": 1,
            }
        ]

    lines = content.splitlines()

    chunks = []
    buffer = []
    current_length = 0
    chunk_no = 1

    for line in lines:

        line_length = (
            len(line) + 1
        )

        if (
            buffer
            and (
                current_length
                + line_length
                > chunk_size
            )
        ):

            chunks.append(
                {
                    **section,
                    "chunk_no":
                        chunk_no,
                    "content":
                        "\n".join(
                            buffer
                        ).strip(),
                }
            )

            buffer = []
            current_length = 0
            chunk_no += 1

        buffer.append(
            line
        )

        current_length += (
            line_length
        )

    if buffer:

        chunks.append(
            {
                **section,
                "chunk_no":
                    chunk_no,
                "content":
                    "\n".join(
                        buffer
                    ).strip(),
            }
        )

    return chunks


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 3500,
    overlap: int = 0,
) -> list[dict]:

    _ = overlap

    sections = extract_sections(
        pages
    )

    chunks = []

    for section in sections:

        for chunk in chunk_large_section(
            section=section,
            chunk_size=chunk_size,
        ):

            # Backward compatibility with the
            # existing intelligence service.
            chunk["page_number"] = (
                chunk.get(
                    "start_page"
                )
            )

            chunks.append(
                chunk
            )

    return chunks


def score_chunk(
    question: str,
    content: str,
    section_title: str | None = None,
    parent_section_title: str | None = None,
) -> float:

    question_tokens = tokenize(
        question
    )

    content_tokens = tokenize(
        content
    )

    if (
        not question_tokens
        or not content_tokens
    ):
        return 0.0

    question_set = set(
        question_tokens
    )

    content_counts = Counter(
        content_tokens
    )

    score = 0.0

    for token in question_set:

        count = content_counts.get(
            token,
            0,
        )

        if count:

            score += (
                1.0
                + min(
                    count,
                    5,
                )
                * 0.20
            )

    title_tokens = set(
        tokenize(
            section_title
            or ""
        )
    )

    parent_tokens = set(
        tokenize(
            parent_section_title
            or ""
        )
    )

    score += (
        len(
            question_set
            & title_tokens
        )
        * 4.0
    )

    score += (
        len(
            question_set
            & parent_tokens
        )
        * 3.0
    )

    responsibility_terms = {
        "responsibility",
        "responsibilities",
        "responsible",
        "authority",
        "authorities",
        "role",
        "roles",
        "duty",
        "duties",
    }

    if (
        question_set
        & responsibility_terms
    ):

        hierarchy_text = (
            (
                section_title
                or ""
            )
            + " "
            + (
                parent_section_title
                or ""
            )
        ).lower()

        if (
            "responsib"
            in hierarchy_text
            or "authorit"
            in hierarchy_text
        ):
            score += 12.0

    question_clean = " ".join(
        question_tokens
    )

    content_clean = " ".join(
        content_tokens
    )

    if (
        len(question_clean) > 5
        and question_clean
        in content_clean
    ):
        score += 5.0

    return score

def expand_related_sections(
    selected: list[dict],
    all_chunks: list[dict],
    limit: int,
) -> list[dict]:

    if not selected:
        return []

    expanded = list(
        selected
    )

    selected_keys = {
        (
            item.get("section_id"),
            item.get("chunk_no"),
        )
        for item in expanded
    }

    # If a major section or one of its children
    # is strongly relevant, include sibling
    # sections belonging to that same parent.
    relevant_parent_numbers = set()

    for item in selected:

        section_number = (
            item.get(
                "section_number"
            )
        )

        parent_number = (
            item.get(
                "parent_section_number"
            )
        )

        section_title = (
            item.get(
                "section_title"
            )
            or ""
        ).lower()

        parent_title = (
            item.get(
                "parent_section_title"
            )
            or ""
        ).lower()

        if (
            "responsib"
            in section_title
            or "authorit"
            in section_title
        ):
            if section_number:
                relevant_parent_numbers.add(
                    section_number
                )

        if (
            "responsib"
            in parent_title
            or "authorit"
            in parent_title
        ):
            if parent_number:
                relevant_parent_numbers.add(
                    parent_number
                )

    if not relevant_parent_numbers:
        return selected[:limit]

    for chunk in all_chunks:

        parent_number = (
            chunk.get(
                "parent_section_number"
            )
        )

        section_number = (
            chunk.get(
                "section_number"
            )
        )

        belongs = (
            parent_number
            in relevant_parent_numbers
            or section_number
            in relevant_parent_numbers
        )

        if not belongs:
            continue

        key = (
            chunk.get(
                "section_id"
            ),
            chunk.get(
                "chunk_no"
            ),
        )

        if key in selected_keys:
            continue

        expanded.append(
            chunk
        )

        selected_keys.add(
            key
        )

    # Once a relevant hierarchy has been identified,
    # preserve all of its sections even when this
    # exceeds the normal semantic top-N slightly.
    expanded.sort(
        key=lambda item: (
            item.get(
                "start_page"
            )
            or 0,
            item.get(
                "section_id"
            )
            or 0,
            item.get(
                "chunk_no"
            )
            or 0,
        )
    )

    return expanded

def retrieve_relevant_chunks(
    question: str,
    pages: list[dict],
    limit: int = 8,
) -> list[dict]:

    chunks = chunk_pages(
        pages
    )

    scored = []

    for chunk in chunks:

        score = score_chunk(
            question=question,
            content=(
                chunk.get(
                    "content"
                )
                or ""
            ),
            section_title=(
                chunk.get(
                    "section_title"
                )
            ),
            parent_section_title=(
                chunk.get(
                    "parent_section_title"
                )
            ),
        )

        if score <= 0:
            continue

        scored.append(
            {
                **chunk,
                "score":
                    round(
                        score,
                        3,
                    ),
            }
        )

    scored.sort(
        key=lambda item:
            item["score"],
        reverse=True,
    )

    initially_selected = (
        scored[:limit]
    )

    selected = (
        expand_related_sections(
            selected=initially_selected,
            all_chunks=chunks,
            limit=limit,
        )
    )

    selected.sort(
        key=lambda item: (
            item.get(
                "start_page"
            )
            or 0,
            item.get(
                "section_id"
            )
            or 0,
            item.get(
                "chunk_no"
            )
            or 0,
        )
    )

    return selected