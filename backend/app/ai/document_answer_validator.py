import re


CLAUSE_PATTERN = re.compile(
    r"\b\d+\.\d+\.\d+\b"
)

CLAUSE_LINE_PATTERN = re.compile(
    r"^\s*"
    r"(?P<clause>\d+\.\d+\.\d+)"
    r"\.?\s+"
    r"(?P<text>.+)"
    r"$"
)

def clean_ocr_clause_text(
    text: str,
) -> str:

    if not text:
        return ""

    text = text.strip()

    # Normalize whitespace
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    # Repair common OCR spacing around &
    text = re.sub(
        r"\s*&\s*",
        " & ",
        text,
    )

    # Repair words accidentally joined after
    # punctuation/known document separators.
    text = re.sub(
        r"EvaluationPolicy\b",
        "Evaluation Policy",
        text,
        flags=re.IGNORECASE,
    )

    # Remove isolated OCR page-number artifacts
    # appearing between normal words:
    #
    # "Policy 7 and Procedure"
    #
    # We only remove a single digit when it is
    # surrounded by alphabetic words.
    text = re.sub(
        r"(?<=[A-Za-z])\s+[0-9]\s+(?=[A-Za-z])",
        " ",
        text,
    )

    # Remove obvious OCR garbage trailing after
    # a completed sentence.
    #
    # Example:
    # "Bank. oe ‘Gerad ise"
    #
    # Conservative rule:
    # after sentence-ending punctuation, remove
    # a very short trailing fragment containing
    # unusual quote characters.
    text = re.sub(
        r"([.!?])\s+"
        r"[A-Za-z]{1,3}\s+"
        r"[‘’`'\"]"
        r"[A-Za-z\s]{1,20}$",
        r"\1",
        text,
    )

    text = re.sub(
        r"\s+([,.;:])",
        r"\1",
        text,
    )

    return text.strip()

def extract_structured_clauses(
    chunks: list[dict],
) -> dict[str, dict]:

    clauses = {}

    for chunk in chunks:

        content = (
            chunk.get("content")
            or ""
        ).strip()

        if not content:
            continue

        section_number = (
            chunk.get(
                "section_number"
            )
        )

        section_title = (
            chunk.get(
                "section_title"
            )
            or "Unknown Section"
        )

        if not section_number:
            continue

        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        current_clause = None
        found_numbered_clause = False
        unnumbered_lines = []

        for index, raw_line in enumerate(
            lines
        ):

            line = raw_line.strip()

            # Remove harmless OCR margin markers.
            line = re.sub(
                r"^[|,;:\s]+",
                "",
                line,
            ).strip()

            if not line:
                continue

            # Skip the section heading itself:
            #
            # 5.5. Legal Services Department
            # 5.2. The President shall
            if index == 0:

                escaped_section = (
                    re.escape(
                        section_number
                    )
                )

                if re.match(
                    rf"^{escaped_section}\.?\s+",
                    line,
                ):
                    continue

            match = (
                CLAUSE_LINE_PATTERN.match(
                    line
                )
            )

            if match:

                found_numbered_clause = True

                current_clause = (
                    match.group(
                        "clause"
                    )
                )

                clauses[current_clause] = {
                    "clause_id":
                        current_clause,

                    "text":
                        match.group(
                            "text"
                        ).strip(),

                    "section_number":
                        section_number,

                    "section_title":
                        section_title,

                    "parent_section_number":
                        chunk.get(
                            "parent_section_number"
                        ),

                    "parent_section_title":
                        chunk.get(
                            "parent_section_title"
                        ),

                    "start_page":
                        chunk.get(
                            "start_page"
                        ),

                    "end_page":
                        chunk.get(
                            "end_page"
                        ),

                    "is_numbered":
                        True,
                }

                continue

            # If a numbered clause has started,
            # ordinary lines belong to that clause.
            if (
                current_clause
                and current_clause in clauses
            ):

                clauses[
                    current_clause
                ]["text"] += (
                    " " + line
                )

                continue

            # No numbered clause exists yet.
            # Preserve the text as an unnumbered
            # responsibility belonging directly
            # to the section owner.
            unnumbered_lines.append(
                line
            )

        if (
            not found_numbered_clause
            and unnumbered_lines
        ):

            synthetic_id = (
                f"{section_number}.__unnumbered__"
            )

            clauses[synthetic_id] = {
                "clause_id":
                    None,

                "text":
                    " ".join(
                        unnumbered_lines
                    ).strip(),

                "section_number":
                    section_number,

                "section_title":
                    section_title,

                "parent_section_number":
                    chunk.get(
                        "parent_section_number"
                    ),

                "parent_section_title":
                    chunk.get(
                        "parent_section_title"
                    ),

                "start_page":
                    chunk.get(
                        "start_page"
                    ),

                "end_page":
                    chunk.get(
                        "end_page"
                    ),

                "is_numbered":
                    False,
            }

    return clauses


def extract_clause_ids(
    text: str,
) -> set[str]:
    """
    Extract policy clause identifiers such as:

    5.1.1
    5.2.4
    10.3.2
    """

    return set(
        CLAUSE_PATTERN.findall(
            text or ""
        )
    )


def extract_evidence_clause_ids(
    chunks: list[dict],
) -> set[str]:

    clause_ids = set()

    for chunk in chunks:

        content = (
            chunk.get("content")
            or ""
        )

        clause_ids.update(
            extract_clause_ids(
                content
            )
        )

    return clause_ids

def group_clauses_by_owner(
    chunks: list[dict],
) -> list[dict]:

    structured = extract_structured_clauses(
        chunks
    )

    owners = {}

    for clause_id, clause in structured.items():

        section_number = (
            clause.get("section_number")
        )

        section_title = (
            clause.get("section_title")
            or "Unknown Section"
        )

        if not section_number:
            continue

        key = (
            section_number,
            section_title,
        )

        if key not in owners:

            owners[key] = {
                "section_number":
                    section_number,

                "section_title":
                    section_title,

                "start_page":
                    clause.get(
                        "start_page"
                    ),

                "end_page":
                    clause.get(
                        "end_page"
                    ),

                "clauses": [],
            }

        owners[key][
            "clauses"
        ].append(
            {
                "clause_id":
                    clause.get(
                        "clause_id"
                    ),

                "text":
                    clean_ocr_clause_text(
                        clause["text"]
                    ),

                "is_numbered":
                    clause.get(
                        "is_numbered",
                        True,
                    ),
            }
        )

    result = list(
        owners.values()
    )

    def section_sort_key(
        owner: dict,
    ):

        number = (
            owner.get(
                "section_number"
            )
            or ""
        )

        try:
            return tuple(
                int(part)
                for part in number.split(".")
            )
        except ValueError:
            return (999999,)

    result.sort(
        key=section_sort_key
    )

    return result

def detect_requested_responsibility_owner(
    question: str,
    owners: list[dict],
) -> str | None:
    """
    Detect whether a responsibility question asks for
    one specific responsibility owner.

    Returns the matching section number, for example:
        5.1 -> Board of Directors
        5.2 -> President

    Returns None when the question is asking for all
    responsibilities.
    """

    normalized_question = (
        " ".join(
            (question or "")
            .lower()
            .strip()
            .split()
        )
    )

    if not normalized_question:
        return None

    # --------------------------------------------------------
    # Explicit aliases
    # --------------------------------------------------------

    aliases = {
        "board of directors": (
            "board",
            "board of directors",
            "the board",
        ),

        "president": (
            "president",
            "the president",
        ),

        "strategy and transformation": (
            "strategy and transformation",
            "vp strategy and transformation",
            "v/p strategy and transformation",
            "v/p- strategy and transformation",
        ),

        "planning and monitoring": (
            "planning and monitoring department",
            "planning & monitoring department",
            "planning and monitoring",
        ),

        "legal services": (
            "legal services department",
            "legal services",
        ),
    }

    # --------------------------------------------------------
    # Match aliases against actual extracted owner titles
    # --------------------------------------------------------

    for owner in owners:

        section_number = (
            owner.get("section_number")
            or ""
        )

        section_title = (
            " ".join(
                (
                    owner.get("section_title")
                    or ""
                )
                .lower()
                .strip()
                .split()
            )
        )

        if not section_number:
            continue

        for canonical, terms in aliases.items():

            if canonical not in section_title:
                continue

            if any(
                term in normalized_question
                for term in terms
            ):
                return section_number

        # --------------------------------------------------------
    # Generic owner-title matching
    # --------------------------------------------------------
    #
    # Only attempt generic owner matching when the question
    # explicitly asks for the responsibilities/duties/roles
    # OF a specific owner.
    #
    # This prevents document-title words such as
    # "Monitoring" from accidentally matching
    # "Planning and Monitoring Department".

    owner_patterns = (
        "responsibilities of ",
        "responsibility of ",
        "duties of ",
        "duty of ",
        "roles of ",
        "role of ",
        "authorities of ",
        "authority of ",
    )

    requested_owner_text = None

    for pattern in owner_patterns:

        if pattern in normalized_question:

            requested_owner_text = (
                normalized_question
                .split(
                    pattern,
                    1,
                )[1]
                .strip()
            )

            break

    # No explicit owner was requested.
    #
    # Example:
    # "What are the responsibilities in the
    # Monitoring and Evaluation Policy?"
    #
    # This must return ALL owners.
    if not requested_owner_text:
        return None

    # Remove common document-reference endings so that
    # only the requested organizational owner is scored.
    document_markers = (
        " in the ",
        " according to ",
        " under the ",
        " from the ",
        " within the ",
    )

    for marker in document_markers:

        if marker in requested_owner_text:

            requested_owner_text = (
                requested_owner_text
                .split(
                    marker,
                    1,
                )[0]
                .strip()
            )

            break

    ignored_words = {
        "shall",
        "department",
        "office",
        "division",
        "directorate",
        "the",
        "and",
        "of",
    }

    requested_words = {
        word.strip(
            ".,:;()[]/-"
        )
        for word
        in requested_owner_text.split()
        if word.strip(
            ".,:;()[]/-"
        )
    }

    best_section = None
    best_score = 0

    for owner in owners:

        section_number = (
            owner.get(
                "section_number"
            )
            or ""
        )

        section_title = (
            owner.get(
                "section_title"
            )
            or ""
        ).lower()

        title_words = {
            word.strip(
                ".,:;()[]/-"
            )
            for word
            in section_title.split()
            if word.strip(
                ".,:;()[]/-"
            )
        }

        meaningful_words = {
            word
            for word in title_words
            if (
                word
                not in ignored_words
                and len(word) >= 3
            )
        }

        score = len(
            meaningful_words
            & requested_words
        )

        if score > best_score:

            best_score = score
            best_section = (
                section_number
            )

    if best_score > 0:
        return best_section

    return None

def clean_responsibility_owner_title(
    title: str,
) -> str:
    """
    Clean responsibility section titles for display only.

    The original extracted section title remains unchanged
    in the document cache/evidence.
    """

    cleaned = (
        " ".join(
            (title or "")
            .strip()
            .split()
        )
    )

    # Remove trailing legal/action wording.
    if cleaned.lower().endswith(" shall"):
        cleaned = cleaned[:-6].strip()

    # Remove unnecessary leading article.
    if cleaned.lower().startswith("the "):
        cleaned = cleaned[4:].strip()

    # Normalize common OCR/punctuation formatting.
    cleaned = cleaned.replace(
        "V/P- ",
        "V/P ",
    )

    return cleaned

def build_responsibility_answer(
    chunks: list[dict],
    document_title: str,
    question: str | None = None,
) -> str | None:

    owners = group_clauses_by_owner(
        chunks
    )

    responsibility_owners = []

    for owner in owners:

        section_number = (
            owner.get(
                "section_number"
            )
            or ""
        )

        matching_chunk = next(
            (
                chunk
                for chunk in chunks
                if (
                    chunk.get(
                        "section_number"
                    )
                    == section_number
                )
            ),
            None,
        )

        if not matching_chunk:
            continue

        parent_title = (
            matching_chunk.get(
                "parent_section_title"
            )
            or ""
        ).lower()

        # Only sections that belong to an
        # Authorities / Responsibilities hierarchy.
        if (
            "responsib" not in parent_title
            and "authorit" not in parent_title
        ):
            continue

        responsibility_owners.append(
            owner
        )

    if not responsibility_owners:
        return None
    
        # --------------------------------------------------------
    # Specific responsibility owner
    # --------------------------------------------------------

    requested_owner = (
        detect_requested_responsibility_owner(
            question=question or "",
            owners=responsibility_owners,
        )
    )

    # Default response:
    # return all responsibility owners.
    lines = [
        (
            f"According to the "
            f"**{document_title}**, "
            f"the responsibilities are:"
        ),
        "",
    ]

    # If the question explicitly asks for one owner,
    # filter the responsibility sections.
    if requested_owner:

        responsibility_owners = [
            owner
            for owner
            in responsibility_owners
            if (
                owner.get(
                    "section_number"
                )
                == requested_owner
            )
        ]

        if not responsibility_owners:
            return None

        owner_title = (
            clean_responsibility_owner_title(
                responsibility_owners[0]
                .get("section_title")
                or "requested role"
            )
        )

        lines = [
            (
                f"According to the "
                f"**{document_title}**, "
                f"the responsibilities of "
                f"**{owner_title}** are:"
            ),
            "",
        ]

    for owner in responsibility_owners:

        section_number = (
            owner.get(
                "section_number"
            )
            or ""
        )

        section_title = (
            clean_responsibility_owner_title(
                owner.get(
                    "section_title"
                )
                or "Unknown Section"
            )
        )

        start_page = (
            owner.get(
                "start_page"
            )
        )

        end_page = (
            owner.get(
                "end_page"
            )
            or start_page
        )

        heading = (
            f"### {section_number} "
            f"{section_title}"
        ).strip()

        if start_page:

            if (
                end_page
                and end_page != start_page
            ):
                heading += (
                    f" — Pages "
                    f"{start_page}-{end_page}"
                )
            else:
                heading += (
                    f" — Page {start_page}"
                )

        lines.append(
            heading
        )

        clauses = (
            owner.get(
                "clauses"
            )
            or []
        )

        for clause in clauses:

            clause_id = (
                clause.get(
                    "clause_id"
                )
            )

            text = (
                clause.get(
                    "text"
                )
                or ""
            ).strip()

            if not text:
                continue

            if clause_id:

                lines.append(
                    f"- **{clause_id}** "
                    f"{text}"
                )

            else:

                lines.append(
                    f"- {text}"
                )

        lines.append("")

    return "\n".join(
        lines
    ).strip()
    
def is_purpose_question(
    question: str,
) -> bool:

    normalized = (
        " ".join(
            (question or "")
            .lower()
            .strip()
            .split()
        )
    )

    indicators = (
        "what is the purpose",
        "what's the purpose",
        "purpose of",
        "purpose for",
    )

    return any(
        indicator in normalized
        for indicator in indicators
    )
    
def build_document_section_answer(
    chunks: list[dict],
    document_title: str,
    section_name: str,
) -> str | None:

    if not chunks:
        return None

    lines = [
        (
            f"According to the "
            f"**{document_title}**, "
            f"the **{section_name}** is:"
        ),
        "",
    ]

    added_content = False

    for chunk in chunks:

        section_number = (
            chunk.get("section_number")
            or ""
        )

        section_title = (
            chunk.get("section_title")
            or ""
        ).strip()

        content = (
            chunk.get("content")
            or ""
        ).strip()

        page = (
            chunk.get("page_number")
            or chunk.get("start_page")
        )

        # Do not print an empty parent heading.
        if not content:
            continue

        heading = ""

        if section_number:
            heading = (
                f"### {section_number}"
            )

            if section_title:
                heading += (
                    f" {section_title}"
                )

            if page:
                heading += (
                    f" — Page {page}"
                )

        if heading:
            lines.append(
                heading
            )

        lines.append(
            content
        )

        lines.append("")
        added_content = True

    if not added_content:
        return None

    return "\n".join(
        lines
    ).strip()
    
def detect_document_summary_intent(
    question: str,
) -> bool:
    """
    Detect whether the user is asking for a summary,
    overview, briefing, or main points of an entire
    document.

    This is generic and must not depend on a specific
    policy or document title.
    """

    normalized = (
        question
        .strip()
        .lower()
    )

    if not normalized:
        return False

    summary_phrases = [
        "summarize",
        "summarise",
        "summary of",
        "give me a summary",
        "give me an overview",
        "overview of",
        "brief me on",
        "brief me about",
        "give me a brief",
        "brief summary",
        "main points",
        "key points",
        "key highlights",
        "major points",
        "important points",
        "what are the main points",
        "what are the key points",
        "what is this document about",
        "what is this policy about",
        "explain this document",
        "explain this policy",
    ]

    return any(
        phrase in normalized
        for phrase in summary_phrases
    )
    
def detect_requested_document_section(
    question: str,
) -> str | None:
    """
    Detect whether the user is asking directly
    for a known document section.

    This returns a conceptual section name.
    The actual cached document heading is matched
    later by the generic section retriever.
    """

    normalized = (
        " ".join(
            (question or "")
            .lower()
            .strip()
            .split()
        )
    )

    if not normalized:
        return None

    section_concepts = {
        "purpose": (
            "purpose",
            "purpose of",
        ),

        "scope": (
            "scope",
            "scope of",
        ),

        "objectives": (
            "objectives",
            "objective",
            "objectives of",
            "objective of",
        ),

        "definitions": (
            "definitions",
            "definition",
            "define",
        ),

        "principles": (
            "principles",
            "principle",
        ),

        "policy statements": (
            "policy statements",
            "policy statement",
        ),

        "governance": (
            "governance",
            "governance structure",
        ),

        "roles and responsibilities": (
            "roles and responsibilities",
        ),

        "authorities and responsibilities": (
            "authorities and responsibilities",
        ),

        "procedures": (
            "procedures",
            "procedure",
        ),

        "requirements": (
            "requirements",
            "requirement",
        ),

        "guidelines": (
            "guidelines",
            "guideline",
        ),

        "exceptions": (
            "exceptions",
            "exception",
        ),

        "compliance": (
            "compliance",
        ),

        "monitoring": (
            "monitoring requirements",
            "monitoring mechanism",
        ),

        "reporting": (
            "reporting requirements",
            "reporting mechanism",
        ),
    }

    for concept, phrases in (
        section_concepts.items()
    ):

        for phrase in phrases:

            if phrase in normalized:
                return concept

    return None
    
def is_responsibility_question(
    question: str,
) -> bool:

    normalized = (
        question
        or ""
    ).lower()

    indicators = (
        "responsibility",
        "responsibilities",
        "responsible for",
        "who is responsible",
        "who shall",
        "duties",
        "duty of",
        "roles and responsibilities",
        "authorities and responsibilities",
    )

    return any(
        indicator in normalized
        for indicator in indicators
    )

def validate_answer_clauses(
    answer: str,
    chunks: list[dict],
) -> dict:

    evidence_clause_ids = (
        extract_evidence_clause_ids(
            chunks
        )
    )

    answer_clause_ids = (
        extract_clause_ids(
            answer
        )
    )

    invalid_clause_ids = (
        answer_clause_ids
        - evidence_clause_ids
    )

    valid_clause_ids = (
        answer_clause_ids
        & evidence_clause_ids
    )

    return {
        "is_valid":
            len(
                invalid_clause_ids
            ) == 0,

        "evidence_clause_ids":
            sorted(
                evidence_clause_ids
            ),

        "answer_clause_ids":
            sorted(
                answer_clause_ids
            ),

        "valid_clause_ids":
            sorted(
                valid_clause_ids
            ),

        "invalid_clause_ids":
            sorted(
                invalid_clause_ids
            ),
    }