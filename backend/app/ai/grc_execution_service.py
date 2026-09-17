import re
import json

from typing import Any

from sqlalchemy.orm import Session

from app.ai.grc_capability_registry import (
    get_grc_capability,
)
from app.ai.grc_prompt_registry import (
    build_grc_system_prompt,
)
from app.ai.document_source_service import (
    search_dms_documents,
)
from app.ai.document_cache_service import (
    get_ready_cached_document,
    retrieve_cached_chunks,
)

from app.ai.providers.factory import (
    get_ai_provider,
)


SINGLE_DOCUMENT_GRC_CAPABILITIES = {
    "document_summary",
    "document_classification",
    "metadata_extraction",
    "procedure_mapping",
    "raci_extraction",
    "cross_reference_mapping",
    "ambiguity_audit",
    "audit_checklist",
    "role_specific_view",
    "employee_faq",
}


def is_single_document_grc_capability(
    capability_code: str,
) -> bool:

    return (
        capability_code
        in SINGLE_DOCUMENT_GRC_CAPABILITIES
    )


def resolve_grc_document(
    database: Session,
    document_query: str,
) -> dict[str, Any]:
    """
    Resolve exactly one DMS document.

    This function only discovers metadata.
    It does not perform authorization and does
    not index or modify documents.
    """

    query = (
        document_query
        or ""
    ).strip()

    if not query:
        raise ValueError(
            "Document query is required."
        )

    documents = search_dms_documents(
        database=database,
        query=query,
        limit=10,
    )

    if not documents:
        return {
            "status": "not_found",
            "document": None,
            "candidates": [],
        }

    # Prefer exact title/description/filename match.
    normalized_query = query.lower()

    exact_matches = []

    for document in documents:

        candidate_values = [
            document.get("file_desc"),
            document.get("filename"),
            document.get("title"),
        ]

        if any(
            str(value or "")
            .strip()
            .lower()
            == normalized_query
            for value in candidate_values
        ):
            exact_matches.append(
                document
            )

        if len(exact_matches) == 1:
                return {
                    "status": "resolved",
                    "document": exact_matches[0],
                    "candidates": exact_matches,
                }

            # -------------------------------------------------
            # Multiple exact DMS matches
            # -------------------------------------------------
            #
            # Prefer the candidate that already has exactly one
            # ready Day 4 document index.
            #
            # Never choose by DMS result order.
            # Never choose when multiple ready indexes exist.
            # -------------------------------------------------

        if len(exact_matches) > 1:

                ready_matches = []

                for document in exact_matches:

                    external_document_id = (
                        document.get("id")
                    )

                    if external_document_id is None:
                        continue

                    try:
                        external_document_id = int(
                            external_document_id
                        )

                    except (TypeError, ValueError):
                        continue

                    cached_document = (
                        get_ready_cached_document(
                            database=database,
                            external_document_id=(
                                external_document_id
                            ),
                        )
                    )

                    if cached_document is not None:
                        ready_matches.append(
                            document
                        )

                if len(ready_matches) == 1:
                    return {
                        "status": "resolved",
                        "document": ready_matches[0],
                        "candidates": exact_matches,
                    }

                # Zero ready matches:
                # we do not know which document is intended.
                #
                # Multiple ready matches:
                # both are legitimate indexed candidates.
                #
                # In either case, remain ambiguous.
                return {
                    "status": "ambiguous",
                    "document": None,
                    "candidates": exact_matches,
                }

        if len(documents) == 1:
            return {
                "status": "resolved",
                "document": documents[0],
                "candidates": documents,
            }

    # Important:
    # do not silently choose among multiple
    # governance documents.
    return {
        "status": "ambiguous",
        "document": None,
        "candidates": documents,
    }


def get_grc_document_cache(
    database: Session,
    document: dict[str, Any],
):
    """
    Resolve an already-indexed Day 4 document.

    GRC execution does not create or rebuild
    document indexes.
    """

    external_document_id = (
        document.get("id")
    )

    if external_document_id is None:
        raise ValueError(
            "Resolved DMS document has no id."
        )

    try:
        external_document_id = int(
            external_document_id
        )

    except (TypeError, ValueError):
        raise ValueError(
            "Resolved DMS document id is invalid."
        )

    return get_ready_cached_document(
        database=database,
        external_document_id=(
            external_document_id
        ),
    )


def build_grc_retrieval_query(
    capability_code: str,
    user_query: str,
) -> str:
    """
    Build a generic evidence-retrieval query.

    This contains operation concepts only.
    It never contains document-specific terms.
    """

    user_query = (
        user_query
        or ""
    ).strip()

    capability_terms = {

        "document_summary":
            "purpose scope requirements "
            "responsibilities exceptions approvals",

        "document_classification":
            "purpose scope shall must should "
            "procedure guideline framework directive",

        "metadata_extraction":
            "document title document id code version "
            "effective date review cycle audience "
            "owner department",

        "procedure_mapping":
            "procedure process steps responsible "
            "role input output record",

        "raci_extraction":
            "responsibility accountable responsible "
            "consulted informed role department",

        "cross_reference_mapping":
            "reference policy regulation directive "
            "law standard form related document",

        "ambiguity_audit":
            "shall must should timely regularly "
            "appropriate sufficient requirement",

        "audit_checklist":
            "shall must mandatory requirement "
            "control evidence compliance monitoring",

        "role_specific_view":
            "responsibility obligation shall must "
            "role department approval",

        "employee_faq":
            "requirements responsibilities process "
            "approval exception employee",
    }

    operation_terms = (
        capability_terms.get(
            capability_code,
            "",
        )
    )

    # Role-specific analysis must be driven primarily
    # by the user's requested role.
    #
    # Adding broad responsibility/department terms here
    # causes unrelated governance roles to outrank the
    # requested role in responsibility-heavy documents.
    if capability_code == "role_specific_view":
        return user_query

    return " ".join(
        part
        for part in [
            user_query,
            operation_terms,
        ]
        if part
    )

def rerank_role_specific_chunks(
    chunks: list[dict],
    user_query: str,
) -> list[dict]:
    """
    Rerank role-specific evidence using phrase and
    discriminative-token matching.

    No organizational role names are hardcoded.
    """

    generic_query_words = {
        "what",
        "which",
        "whose",
        "obligation",
        "obligations",
        "responsibility",
        "responsibilities",
        "requirement",
        "requirements",
        "rule",
        "rules",
        "under",
        "from",
        "this",
        "that",
        "does",
        "have",
        "are",
        "for",
        "the",
    }

    def normalize_word(
        word: str,
    ) -> str:

        word = (
            word.lower()
            .strip(
                ".,:;!?()[]{}'\"/"
            )
        )

        if (
            len(word) > 5
            and word.endswith("s")
            and not word.endswith("ss")
        ):
            word = word[:-1]

        return word

    raw_words = [
        normalize_word(word)
        for word in (
            user_query
            or ""
        ).split()
    ]

    role_words = [
        word
        for word in raw_words
        if (
            word
            and len(word) >= 4
            and word
            not in generic_query_words
        )
    ]

    if not role_words:
        return chunks

    role_word_set = set(
        role_words
    )

    # Count how common each requested-role word is
    # across candidate section titles.
    #
    # A word appearing everywhere ("credit") is less
    # useful than a more discriminative role word.
    title_frequency = {
        word: 0
        for word in role_word_set
    }

    prepared_chunks = []

    for position, chunk in enumerate(
        chunks
    ):

        section = (
            chunk.get("section_title")
            or ""
        )

        content = (
            chunk.get("content")
            or ""
        )

        section_words = {
            normalize_word(word)
            for word in section.split()
            if normalize_word(word)
        }

        opening_words = {
            normalize_word(word)
            for word in content[:900].split()
            if normalize_word(word)
        }

        for word in role_word_set:

            if word in section_words:
                title_frequency[word] += 1

        prepared_chunks.append(
            (
                position,
                chunk,
                section_words,
                opening_words,
            )
        )

    scored = []

    for (
        position,
        chunk,
        section_words,
        opening_words,
    ) in prepared_chunks:

        score = 0.0

        section_matches = (
            role_word_set
            & section_words
        )

        opening_matches = (
            role_word_set
            & opening_words
        )

        # Section-title matches are strongest.
        for word in section_matches:

            frequency = max(
                title_frequency.get(
                    word,
                    1,
                ),
                1,
            )

            score += (
                12.0 / frequency
            )

        # Opening evidence is useful, but weaker.
        for word in opening_matches:

            frequency = max(
                title_frequency.get(
                    word,
                    1,
                ),
                1,
            )

            score += (
                6.0 / frequency
            )

        # Strong bonus when multiple requested-role
        # words occur together.
        combined_matches = (
            role_word_set
            & (
                section_words
                | opening_words
            )
        )

        if len(combined_matches) >= 2:
            score += 20.0

        scored.append(
            (
                score,
                position,
                chunk,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    return [
        item[2]
        for item in scored
    ]
    
def build_role_validation_prompt(
    user_query: str,
    chunks: list[dict],
) -> str:

    blocks = []

    for index, chunk in enumerate(
        chunks,
        1,
    ):
        blocks.append(
            "\n".join(
                [
                    f"CHUNK {index}",
                    (
                        "SECTION: "
                        f"{chunk.get('section_number') or ''} "
                        f"{chunk.get('section_title') or ''}"
                    ),
                    (
                        "CONTENT:\n"
                        + (
                            chunk.get("content")
                            or ""
                        )[:1200]
                    ),
                ]
            )
        )

    evidence = "\n\n---\n\n".join(
        blocks
    )

    return f"""
USER REQUEST:
{user_query}

CANDIDATE DOCUMENT EVIDENCE:
{evidence}

TASK:
Select chunks that provide evidence applicable to the
role or role category requested by the user.

A chunk may be selected when the document itself shows
that:

1. the requested role is explicitly named; OR
2. a closely matching role title is explicitly named; OR
3. the requested role is explicitly included in a
   broader operational group or role category; OR
4. the chunk establishes that a broader role category
   is subject to the document and another supplied
   chunk assigns obligations to that category.

ROLE MATCHING RULES:

- Base role relationships only on wording in the
  supplied evidence.
- Minor grammatical variations such as singular/plural
  may match.
- Closely matching occupational wording may match only
  when the evidence itself supports the relationship.
- A shared business word alone is NOT enough.
- "credit" appearing in two role titles does not make
  those roles equivalent.
- A senior manager, chief, director, committee, board,
  or department is not automatically equivalent to an
  operational officer or performer.
- Do not infer organizational hierarchy from general
  knowledge.
- Do not invent synonyms that are absent from the
  evidence.

IMPORTANT:

Classify selected evidence into two categories:

1. applicability
   Evidence establishing that the requested role,
   closely matching role, or broader supported role
   category is covered by the document.

2. obligations
   Evidence assigning actual duties, requirements,
   prohibitions, responsibilities, or controls to
   that supported role/category.

A chunk describing duties of a distinctly different
role must NOT be selected merely because it concerns
the same business area.

Return valid JSON only:

{{
  "applicability": [1, 2],
  "obligations": [3, 4]
}}

Use only supplied chunk numbers.

If applicability cannot be established, return:

{{
  "applicability": [],
  "obligations": []
}}
""".strip()

def retrieve_grc_evidence(
    database: Session,
    document_index_id: int,
    capability_code: str,
    user_query: str,
    limit: int = 12,
) -> list[dict]:
    """
    Reuse the frozen Day 4 chunk retriever.
    """

    retrieval_query = (
        build_grc_retrieval_query(
            capability_code=(
                capability_code
            ),
            user_query=user_query,
        )
    )

        # Retrieve a wider candidate set for role analysis,
    # then rerank locally. Other GRC capabilities keep
    # their existing Day 4 retrieval behavior.
    retrieval_limit = (
        max(limit * 2, 20)
        if capability_code
        == "role_specific_view"
        else limit
    )

    # Role-specific analysis needs a wider candidate pool.
    candidate_limit = (
        30
        if capability_code == "role_specific_view"
        else limit
    )

    chunks = retrieve_cached_chunks(
        database=database,
        document_index_id=document_index_id,
        question=retrieval_query,
        limit=candidate_limit,
    )

    if (
        capability_code
        == "role_specific_view"
    ):
        chunks = (
            rerank_role_specific_chunks(
                chunks=chunks,
                user_query=user_query,
            )
        )

    return chunks[:limit]

def is_procedural_evidence(
    chunk: dict,
) -> bool:
    """
    Return True only when a chunk contains evidence of
    an actual operational process, procedure, workflow,
    or ordered execution sequence.

    Process-like section titles help identify candidates,
    but are not sufficient by themselves.
    """

    section = re.sub(
        r"\s+",
        " ",
        str(chunk.get("section_title") or ""),
    ).strip().lower()

    content = re.sub(
        r"\s+",
        " ",
        str(chunk.get("content") or ""),
    ).strip().lower()

    if not content:
        return False

    # ---------------------------------------------
    # Reject pure responsibility/governance lists
    # ---------------------------------------------
    responsibility_patterns = (
        r"\bauthority and responsibilit",
        r"\bduties and responsibilit",
        r"\bfollowing responsibilities\b",
        r"\bfollowing authority and responsibilities\b",
    )

    if any(
        re.search(pattern, content)
        for pattern in responsibility_patterns
    ):
        return False

    if re.search(
        r"\bauthority\s+and\s+responsibilit",
        section,
    ):
        return False

    # ---------------------------------------------
    # Reject obvious objective-only material
    # ---------------------------------------------
    objective_patterns = (
        r"\bobjectives?\s+of\b",
        r"\bthe objectives?\b",
        r"\bpurpose\s+of\b",
    )

    if any(
        re.search(pattern, content)
        for pattern in objective_patterns
    ):
        return False

    # ---------------------------------------------
    # Explicit sequence language = strong evidence
    # ---------------------------------------------
    sequence_patterns = (
        r"\bfirst\b.{0,300}\bthen\b",
        r"\bthen\b.{0,300}\bafter\b",
        r"\bafter\b.{0,300}\bshall\b",
        r"\bbefore\b.{0,300}\bshall\b",
        r"\bnext step\b",
        r"\bstep\s*\d+\b",
        r"\bstep\s+(?:one|two|three|four|five)\b",
        r"\bfollowing steps\b",
        r"\bprocess shall\b",
        r"\bprocedure shall\b",
    )

    if any(
        re.search(pattern, content)
        for pattern in sequence_patterns
    ):
        return True

    # ---------------------------------------------
    # Detect numbered operational rules
    # ---------------------------------------------
    numbered_items = re.findall(
        r"(?:^|\s)(\d{1,2})[\.\)]\s+",
        content,
    )

    operational_patterns = (
        r"\bshall\s+be\s+communicated\b",
        r"\bshall\s+be\s+submitted\b",
        r"\bshall\s+be\s+prepared\b",
        r"\bshall\s+be\s+reviewed\b",
        r"\bshall\s+be\s+approved\b",
        r"\bshall\s+be\s+signed\b",
        r"\bshall\s+be\s+forwarded\b",
        r"\bshall\s+be\s+recorded\b",
        r"\bshall\s+be\s+maintained\b",
        r"\bshall\s+be\s+kept\b",
        r"\bshall\s+be\s+obtained\b",
        r"\bshall\s+be\s+verified\b",
        r"\bshall\s+be\s+executed\b",
        r"\bshall\s+submit\b",
        r"\bshall\s+communicate\b",
        r"\bshall\s+forward\b",
        r"\bshall\s+review\b",
        r"\bshall\s+approve\b",
        r"\bmay\s+submit\b",
        r"\bwithin\s+\d+\s+days?\b",
    )

    operational_score = sum(
        1
        for pattern in operational_patterns
        if re.search(pattern, content)
    )

    # A numbered list plus multiple operational
    # instructions is evidence of a process even when
    # the document does not literally say "Step".
    if (
        len(numbered_items) >= 2
        and operational_score >= 2
    ):
        return True

    # ---------------------------------------------
    # Process structure with multiple activities
    # ---------------------------------------------
    process_activity_terms = (
        "origination",
        "appraisal",
        "analysis",
        "approval",
        "decision",
        "contract",
        "disbursement",
        "follow-up",
        "follow up",
        "monitoring",
        "collection",
        "recovery",
    )

    activity_count = sum(
        1
        for term in process_activity_terms
        if term in content
    )

    process_statement = bool(
        re.search(
            r"\b(?:credit\s+)?process\s+shall\b",
            content,
        )
    )

    if (
        process_statement
        and activity_count >= 3
    ):
        return True

    return False

def discover_procedure_sections(
    database: Session,
    document_index_id: int,
) -> list[str]:
    """
    Discover likely process/procedure sections from the
    document's own section catalog.

    This does not contain document-specific section names.
    """

    from app.models.document_chunk import DocumentChunk

    rows = (
        database.query(
            DocumentChunk.section_title
        )
        .filter(
            DocumentChunk.document_index_id
            == document_index_id
        )
        .all()
    )

    procedural_terms = (
        "procedure",
        "process",
        "processing",
        "origination",
        "analysis",
        "appraisal",
        "decision",
        "execution",
        "workflow",
        "follow-up",
        "follow up",
        "monitoring",
        "collection",
        "recovery",
    )

    excluded_terms = (
        "authority and responsibility",
        "duties and responsibilities",
    )

    discovered = []
    seen = set()

    for row in rows:

        section = str(
            row[0] or ""
        ).strip()

        if not section:
            continue

        normalized = re.sub(
            r"\s+",
            " ",
            section,
        ).strip().lower()

        if any(
            term in normalized
            for term in excluded_terms
        ):
            continue

        if not any(
            term in normalized
            for term in procedural_terms
        ):
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        discovered.append(section)

    return discovered

def extract_numbered_procedure_items(
    chunks: list[dict],
) -> list[dict]:
    """
    Deterministically extract numbered procedural items
    from already-validated procedural evidence.

    Handles common OCR noise around numbered items while
    avoiding section numbers such as "4.1." or "7." in
    the section heading.

    No missing steps, roles, sequence, or relationships
    are inferred.
    """

    processes = []

    for chunk in chunks:

        raw_content = str(
            chunk.get("content") or ""
        ).strip()

        if not raw_content:
            continue

        section_title = str(
            chunk.get("section_title") or ""
        ).strip()

        # -------------------------------------------------
        # Preserve line structure first.
        # This makes section-heading removal safer than
        # flattening everything immediately.
        # -------------------------------------------------
        lines = [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in raw_content.splitlines()
        ]

        lines = [
            line
            for line in lines
            if line
        ]

        if not lines:
            continue

        # -------------------------------------------------
        # Remove leading document section heading.
        #
        # Examples:
        #   4.1. Credit Processing
        #   7. CREDIT DECISION EXECUTION & LOAN FILE
        #      MANAGEMENT
        #
        # We only remove material before the first genuine
        # numbered procedure item.
        # -------------------------------------------------
        first_item_index = None

        for index, line in enumerate(lines):

            if re.match(
                r"^[\|\[\]{}Eeqa7'`,._\- ]*"
                r"\d{1,2}\s*[\.\)]\s+"
                r"[A-Za-z]",
                line,
            ):
                # Reject decimal section headings such as:
                # 4.1. Credit Processing
                if re.match(
                    r"^\d+\.\d+\.",
                    line,
                ):
                    continue

                first_item_index = index
                break

        if first_item_index is None:
            continue

        lines = lines[first_item_index:]

        content = " ".join(lines)

        content = re.sub(
            r"\s+",
            " ",
            content,
        ).strip()

        # -------------------------------------------------
        # OCR cleanup ONLY around numbered item boundaries.
        #
        # Example from the scanned document:
        #
        # "| 7 Jaa it 7sLoan disbursement shall..."
        #
        # We do not attempt to repair the sentence itself.
        # We only recover the numbered boundary.
        # -------------------------------------------------
        content = re.sub(
            r"(?i)"
            r"(?<!\d)"
            r"[\|\[\]{}'`,._\- ]*"
            r"(\d{1,2})"
            r"\s+"
            r"(?:[A-Za-z]{1,12}\s+){0,4}"
            r"(?:\d+[A-Za-z]*)?"
            r"\s*"
            r"(?=(?:loan\s+disbursement)\b)",
            r" \1. ",
            content,
        )

        # -------------------------------------------------
        # Standard numbered boundaries.
        #
        # Number must:
        # - not be part of another number
        # - be followed by "." or ")"
        # - not be followed by another digit + "."
        #
        # Therefore "4.1." cannot become item 4.
        # -------------------------------------------------
        pattern = re.compile(
            r"(?<![\d./])"
            r"(\d{1,2})"
            r"\s*[\.\)]"
            r"(?!\d)"
            r"\s*"
            r"(?=[A-Z])"
        )

        matches = list(
            pattern.finditer(content)
        )
        
        # -------------------------------------------------
        # Remove a numbered section heading when it appears
        # before the real procedure item sequence.
        #
        # Example:
        #   7. CREDIT DECISION EXECUTION & LOAN FILE MANAGEMENT
        #   1. Any credit decision shall...
        #
        # The heading number is not a procedure step.
        # -------------------------------------------------
        if len(matches) >= 2:

            first_number = int(
                matches[0].group(1)
            )

            second_number = int(
                matches[1].group(1)
            )

            first_text_start = matches[0].end()
            first_text_end = matches[1].start()

            first_text = content[
                first_text_start:first_text_end
            ].strip()

            # A numbered heading followed by item 1 is structural,
            # not an operational step.
            #
            # Require short heading-like text so we do not remove
            # a legitimate procedure item that happens to precede
            # another sequence.
            if (
                first_number != 1
                and second_number == 1
                and len(first_text) <= 160
                and not re.search(
                    r"\b("
                    r"shall|must|required|responsible|"
                    r"submit|communicate|prepare|review|"
                    r"approve|register|maintain|disburse"
                    r")\b",
                    first_text,
                    re.IGNORECASE,
                )
            ):
                matches = matches[1:]

        if not matches:
            continue

        items = []

        for index, match in enumerate(matches):

            start = match.end()

            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(content)
            )

            text = content[start:end].strip()

            text = re.sub(
                r"\s+",
                " ",
                text,
            ).strip()

            if not text:
                continue

            number = int(
                match.group(1)
            )

            items.append(
                {
                    "number": number,
                    "action": text,
                    "section_title": section_title,
                    "clause_id": chunk.get(
                        "clause_id"
                    ),
                    "page_number": chunk.get(
                        "page_number"
                    ),
                }
            )

        if not items:
            continue

        processes.append(
            {
                "process_name": section_title,
                "page_number": chunk.get(
                    "page_number"
                ),
                "clause_id": chunk.get(
                    "clause_id"
                ),
                "items": items,
            }
        )

    return processes

def extract_explicit_procedure_roles(
    action: str,
) -> list[str]:
    """
    Extract explicitly stated responsible actors from one
    grounded procedure item.

    Conservative:
    - no role inference
    - no organization-specific role dictionary
    - actor must be attached to an explicit action,
      responsibility, assignment, or coordination phrase
    """

    text = re.sub(
        r"\s+",
        " ",
        str(action or ""),
    ).strip()

    if not text:
        return []

    roles: list[str] = []

    def add_role(value: str | None) -> None:
        if not value:
            return

        role = re.sub(
            r"\s+",
            " ",
            value,
        ).strip(" ,.;:|-")

        role = re.sub(
            r"^(?:the|a|an)\s+",
            "",
            role,
            flags=re.IGNORECASE,
        )

        role = re.sub(
            r"^responsible\s+",
            "",
            role,
            flags=re.IGNORECASE,
        )

        # Remove qualification text from a role.
        role = re.split(
            r"\s+other\s+than\b",
            role,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if not role or len(role) < 4:
            return

        if len(role.split()) > 12:
            return

        rejected = {
            "bank",
            "customer",
            "borrower",
            "guarantor",
            "committee members",
            "movable property",
            "credit decision",
            "loan",
            "loan contract",
            "security contract",
        }

        if role.lower() in rejected:
            return

        # If a shorter clean role already exists, do not
        # retain a longer qualification containing it.
        for existing in roles:
            if (
                existing.lower() in role.lower()
                and existing.lower() != role.lower()
            ):
                return

        # If this is the cleaner/shorter form, remove the
        # previously captured expanded form.
        roles[:] = [
            existing
            for existing in roles
            if not (
                role.lower() in existing.lower()
                and role.lower() != existing.lower()
            )
        ]

        if role.lower() not in {
            existing.lower()
            for existing in roles
        }:
            roles.append(role)

    # 1. Explicit passive assignment:
    # "shall be communicated by the Relationship Manager"
    # "shall always be designed by the legal service department"
    for match in re.finditer(
        r"\b(?:shall|must)\s+"
        r"(?:always\s+)?be\s+"
        r"[A-Za-z][A-Za-z\-]*"
        r"(?:\s+[A-Za-z][A-Za-z\-]*){0,4}"
        r"\s+by\s+(?:the\s+|a\s+|an\s+)?"
        r"([A-Za-z][A-Za-z&/\- ]{2,80}?)"
        r"(?="
        r"\s+(?:to|through|upon|after|before|for|"
        r"in accordance|whenever|other than)"
        r"|[,.;]|$"
        r")",
        text,
        re.IGNORECASE,
    ):
        add_role(match.group(1))

    # 2. Special passive re-appraisal boundary.
    for match in re.finditer(
        r"\b(?:shall|must)\s+be\s+"
        r"re-?appraised\s+by\s+"
        r"(?:the\s+|a\s+|an\s+)?"
        r"(.+?)"
        r"(?=\s+other\s+than\b|[,.;]|$)",
        text,
        re.IGNORECASE,
    ):
        add_role(match.group(1))

    # 3. Explicit actor + shall/can + action.
    #
    # Actor may occur after a clause introducer:
    # "However, if ..., the responsible X, ... shall prepare"
    # "In such cases, the X can advise..."
    actor_action_pattern = re.compile(
        r"(?:^|[.;]\s+|,\s+)"
        r"(?:however,\s+|additionally,\s+|"
        r"in\s+such\s+cases,\s+)?"
        r"(?:the\s+|a\s+|an\s+)?"
        r"(?:responsible\s+)?"
        r"([A-Za-z][A-Za-z&/\- ]{2,100}?)"
        r"(?:,\s+in\s+coordination\s+with\s+"
        r"(?:the\s+)?"
        r"([A-Za-z][A-Za-z&/\- ]{2,80}?))?"
        r"\s*,?\s+"
        r"(?:shall|must|can)\s+"
        r"(prepare|review|approve|communicate|"
        r"register|maintain|submit|decide|design|"
        r"check|verify|undertake|deliberate|"
        r"ascertain|advise)",
        re.IGNORECASE,
    )

    for match in actor_action_pattern.finditer(text):
        add_role(match.group(1))
        add_role(match.group(2))

    # 4. Explicit entrusted responsibility.
    for match in re.finditer(
        r"(?:^|[.;]\s+)"
        r"(?:the\s+)?"
        r"([A-Za-z][A-Za-z&/,\- ]{2,120}?)"
        r"\s+(?:is|are|shall\s+be)\s+"
        r"entrusted\s+with\b",
        text,
        re.IGNORECASE,
    ):
        add_role(match.group(1))

    # 5. Explicit responsibility statement.
    for match in re.finditer(
        r"(?:^|[.;]\s+)"
        r"(?:a\s+|an\s+|the\s+)?"
        r"(?:designated\s+)?"
        r"(.{4,120}?)"
        r"\s+is\s+responsible\s+(?:to|for)\b",
        text,
        re.IGNORECASE,
    ):
        actor = re.sub(
            r"\s+or\s+individual/jointly.*$",
            "",
            match.group(1),
            flags=re.IGNORECASE,
        )

        add_role(actor)

    # 6. Explicit coordination participant.
    for match in re.finditer(
        r"\bin\s+coordination\s+with\s+"
        r"(?:the\s+)?"
        r"([A-Za-z][A-Za-z&/\- ]{2,80}?)"
        r"(?=\s*,?\s+shall\b|[,.;])",
        text,
        re.IGNORECASE,
    ):
        add_role(match.group(1))

    return roles

def render_procedure_mapping(
    chunks: list[dict],
) -> str:
    """
    Render a deterministic, grounded procedure map from
    already-validated procedural evidence.

    No LLM generation.
    No inferred roles.
    No inferred steps.
    """

    processes = extract_numbered_procedure_items(
        chunks
    )

    if not processes:
        return (
            "Information not found in internal documents"
        )

    output: list[str] = []

    for process in processes:

        process_name = (
            process.get("process_name")
            or "Information not found in internal documents"
        )

        page_number = process.get("page_number")
        clause_id = process.get("clause_id")

        output.append(
            f"### Process/Procedure: {process_name}"
        )

        if clause_id:
            output.append(
                f"Source Clause: {clause_id}"
            )

        if page_number is not None:
            output.append(
                f"Source Page: {page_number}"
            )

        output.append("")

        for item in process.get("items", []):

            number = item.get("number")
            action = str(
                item.get("action") or ""
            ).strip()

            if not action:
                continue

            roles = extract_explicit_procedure_roles(
                action
            )

            responsible = (
                ", ".join(roles)
                if roles
                else (
                    "Information not found in "
                    "internal documents"
                )
            )

            output.append(
                f"#### Step/Rule {number}"
            )

            output.append(
                f"Action: {action}"
            )

            output.append(
                f"Responsible Role/Unit: {responsible}"
            )

            source_parts = []

            if process_name:
                source_parts.append(
                    f"Section: {process_name}"
                )

            if clause_id:
                source_parts.append(
                    f"Clause: {clause_id}"
                )

            if page_number is not None:
                source_parts.append(
                    f"Page: {page_number}"
                )

            if source_parts:
                output.append(
                    "Source: "
                    + " | ".join(source_parts)
                )

            output.append("")

    rendered = "\n".join(output).strip()

    return (
        rendered
        if rendered
        else (
            "Information not found in internal documents"
        )
    )

def retrieve_discovered_procedure_chunks(
    database: Session,
    document_index_id: int,
    section_titles: list[str],
    limit: int = 24,
) -> list[dict]:
    """
    Retrieve chunks belonging to dynamically discovered
    procedure/process sections.

    Section names come from the document itself.
    """

    from app.models.document_chunk import DocumentChunk

    if not section_titles:
        return []

    rows = (
        database.query(DocumentChunk)
        .filter(
            DocumentChunk.document_index_id
            == document_index_id,
            DocumentChunk.section_title.in_(
                section_titles
            ),
        )
        .order_by(
            DocumentChunk.page_number.asc(),
            DocumentChunk.id.asc(),
        )
        .limit(limit)
        .all()
    )

    chunks = []

    for row in rows:
        chunks.append(
            {
                "id": row.id,
                "content": row.content,
                "section_title": row.section_title,
                "clause_id": getattr(
                    row,
                    "clause_id",
                    None,
                ),
                "page_number": row.page_number,
            }
        )

    return chunks

def format_grc_evidence(
    document: dict[str, Any],
    chunks: list[dict],
) -> str:
    """
    Preserve document ownership and evidence
    location for every supplied chunk.
    """

    title = (
        document.get("file_desc")
        or document.get("title")
        or document.get("filename")
        or "Unknown Document"
    )

    blocks = []

    for chunk in chunks:

        page = (
            chunk.get("page_number")
            or chunk.get("start_page")
            or "Unknown"
        )

        section = (
            chunk.get("section_title")
            or "Unknown"
        )

        section_number = (
            chunk.get("section_number")
            or ""
        )

        content = (
            chunk.get("content")
            or ""
        ).strip()

        if not content:
            continue

        section_label = " ".join(
            part
            for part in [
                str(section_number).strip(),
                str(section).strip(),
            ]
            if part
        )

        blocks.append(
            "\n".join(
                [
                    f"DOCUMENT: {title}",
                    f"PAGE: {page}",
                    (
                        "SECTION: "
                        f"{section_label or 'Unknown'}"
                    ),
                    "EVIDENCE:",
                    content,
                ]
            )
        )

    return "\n\n---\n\n".join(
        blocks
    )

def classify_role_evidence(
    chunks: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Separate direct obligation evidence from supporting
    applicability/context evidence.

    OCR-tolerant and generic. No role names, document
    names, or section numbers are hardcoded.
    """

    direct = []
    supporting = []

    normative_patterns = (
        r"\bshall\b",
        r"\bmust\b",
        r"\brequired\s+to\b",
        r"\bresponsib\w*\s+for\b",
        r"\baccountab\w*\s+for\b",
        r"\bexpected\s+to\b",
        r"\bobligat\w*\b",
        r"\bdut(?:y|ies)\b",
    )

    responsibility_patterns = (
        r"\bfollow\w*\s+responsib\w*",
        r"\bresponsib\w*\s*:",
        r"\bauthorit\w*\s+and\s+responsib\w*",
    )

    for chunk in chunks:

        content = (
            chunk.get("content")
            or ""
        )

        # Normalize OCR whitespace without altering
        # the original evidence stored in the chunk.
        normalized = re.sub(
            r"\s+",
            " ",
            content.lower(),
        ).strip()
        
        section_title = (
            chunk.get("section_title")
            or ""
        ).lower()

        context_section_patterns = (
            r"\bscope\b",
            r"\bobjective\w*\b",
            r"\bpurpose\b",
            r"\bapplicab\w*\b",
            r"\bbackground\b",
            r"\bintroduction\b",
        )

        is_context_section = any(
            re.search(
                pattern,
                section_title,
            )
            for pattern in context_section_patterns
        )

        normative_score = sum(
            1
            for pattern in normative_patterns
            if re.search(
                pattern,
                normalized,
            )
        )

        responsibility_score = sum(
            1
            for pattern in responsibility_patterns
            if re.search(
                pattern,
                normalized,
            )
        )

        # Direct evidence must contain actual normative
        # or responsibility-assignment language.
        if is_context_section:

            # Scope, objectives, purpose and similar sections
            # establish applicability/context unless they
            # explicitly assign responsibilities.
            if responsibility_score > 0:
                direct.append(chunk)
            else:
                supporting.append(chunk)

        elif (
            normative_score > 0
            or responsibility_score > 0
        ):
            direct.append(chunk)

        else:
            supporting.append(chunk)

    return direct, supporting

def prepare_single_document_grc(
    database: Session,
    capability_code: str,
    user_query: str,
    document_query: str,
) -> dict[str, Any]:
    """
    Prepare a grounded GRC task.

    Important:
    - no authorization bypass
    - no indexing
    - no model call
    - no modification of Day 4 behavior

    Authorization must occur before this function
    is called by an API/orchestrator.
    """

    capability = get_grc_capability(capability_code)

    if capability is None:
        raise ValueError(
            "Unknown GRC capability: "
            f"{capability_code}"
        )

    if not is_single_document_grc_capability(capability_code):
        raise ValueError(
            "Capability is not a single-document GRC operation: "
            f"{capability_code}"
        )

    resolution = resolve_grc_document(
        database=database,
        document_query=document_query,
    )

    if resolution["status"] != "resolved":
        return {
            "status": resolution["status"],
            "capability": capability_code,
            "document": None,
            "candidates": resolution["candidates"],
            "system_prompt": None,
            "prompt": None,
            "evidence_count": 0,
        }

    document = resolution["document"]

    cached_document = get_grc_document_cache(
        database=database,
        document=document,
    )

    if cached_document is None:
        return {
            "status": "not_indexed",
            "capability": capability_code,
            "document": document,
            "candidates": [],
            "system_prompt": None,
            "prompt": None,
            "evidence_count": 0,
        }

    chunks = retrieve_grc_evidence(
        database=database,
        document_index_id=cached_document.id,
        capability_code=capability_code,
        user_query=user_query,
    )

    # ---------------------------------------------------------
    # Procedure mapping:
    # accept only verified procedural evidence.
    #
    # If normal semantic retrieval does not locate genuine
    # procedural evidence, perform a generic second pass using
    # section names discovered from the document itself.
    # ---------------------------------------------------------
    if capability_code == "procedure_mapping":

        procedural_chunks = [
            chunk
            for chunk in chunks
            if is_procedural_evidence(chunk)
        ]

        if not procedural_chunks:

            procedure_sections = discover_procedure_sections(
                database=database,
                document_index_id=cached_document.id,
            )

            second_pass_chunks = (
                retrieve_discovered_procedure_chunks(
                    database=database,
                    document_index_id=cached_document.id,
                    section_titles=procedure_sections,
                    limit=24,
                )
            )

            procedural_chunks = [
                chunk
                for chunk in second_pass_chunks
                if is_procedural_evidence(chunk)
            ]

        chunks = procedural_chunks


    if capability_code == "role_specific_view":
        chunks = validate_role_evidence(
            user_query=user_query,
            chunks=chunks,
        )

    if not chunks:
        return {
            "status": "no_evidence",
            "capability": capability_code,
            "document": document,
            "candidates": [],
            "system_prompt": None,
            "prompt": None,
            "evidence_count": 0,
        }

    if capability_code == "role_specific_view":
        role_direct_chunks, role_supporting_chunks = (
            classify_role_evidence(chunks=chunks)
        )

        

        if not role_direct_chunks:
            return {
                "status": "no_evidence",
                "capability": capability_code,
                "document": document,
                "candidates": [],
                "system_prompt": None,
                "prompt": None,
                "evidence_count": 0,
            }

        direct_evidence = format_grc_evidence(
            document=document,
            chunks=role_direct_chunks,
        )
        supporting_evidence = (
            format_grc_evidence(
                document=document,
                chunks=role_supporting_chunks,
            )
            if role_supporting_chunks
            else ""
        )

        evidence = (
            "DIRECT ROLE OBLIGATION EVIDENCE:\n"
            f"{direct_evidence}"
        )
    else:
        evidence = format_grc_evidence(
            document=document,
            chunks=chunks,
        )

    if not evidence:
        return {
            "status": "no_evidence",
            "capability": capability_code,
            "document": document,
            "candidates": [],
            "system_prompt": None,
            "prompt": None,
            "evidence_count": 0,
        }

    system_prompt = build_grc_system_prompt(capability_code)

    prompt = (
        "USER REQUEST:\n"
        f"{user_query.strip()}\n\n"
        "AUTHORIZED DOCUMENT EVIDENCE:\n"
        f"{evidence}\n\n"
        "Perform the requested GRC task now. "
        "Use only the supplied evidence."
    )

    return {
        "status": "ready",
        "capability": capability_code,
        "document": document,
        "document_index_id": cached_document.id,
        "evidence_chunks": chunks,
        "system_prompt": system_prompt,
        "prompt": prompt,
        "evidence_count": len(chunks),
    }

def is_distinct_named_role_section(
    section_title: str,
    query_words: set[str],
) -> bool:
    """
    Detect a specifically named role title that is
    narrower/different from the requested role.

    Generic: no NIB role names are hardcoded.
    """

    if not section_title:
        return False

    def normalize_word(word: str) -> str:
        word = (
            word.lower()
            .strip(".,:;!?()[]{}'\"/")
        )

        if (
            len(word) > 5
            and word.endswith("s")
            and not word.endswith("ss")
        ):
            word = word[:-1]

        return word

    # Remove section numbering.
    title_words = {
        normalize_word(word)
        for word in section_title.split()
        if (
            normalize_word(word)
            and not normalize_word(word).replace(
                ".",
                "",
            ).isdigit()
        )
    }

    role_modifiers = {
        "chief",
        "deputy",
        "director",
        "manager",
        "head",
        "board",
        "committee",
        "executive",
        "president",
        "vice",
        "supervisor",
        "coordinator",
    }

    has_specific_modifier = bool(
        title_words & role_modifiers
    )

    if not has_specific_modifier:
        return False

    # A specifically modified role is accepted only
    # when those modifiers were themselves requested.
    unrequested_modifiers = (
        title_words
        & role_modifiers
        - query_words
    )

    return bool(
        unrequested_modifiers
    )
 
def validate_role_evidence(
    user_query: str,
    chunks: list[dict],
) -> list[dict]:
    """
    Deterministically select evidence applicable to a
    requested role.

    The validator does not invent organizational
    relationships. It uses lexical evidence contained
    in the retrieved document chunks.
    """

    if not chunks:
        return []

    stop_words = {
        "what",
        "which",
        "whose",
        "obligation",
        "obligations",
        "responsibility",
        "responsibilities",
        "requirement",
        "requirements",
        "rule",
        "rules",
        "under",
        "from",
        "this",
        "that",
        "does",
        "have",
        "are",
        "for",
        "the",
    }

    def normalize_word(
        word: str,
    ) -> str:

        word = (
            word.lower()
            .strip(
                ".,:;!?()[]{}'\"/"
            )
        )

        if (
            len(word) > 5
            and word.endswith("s")
            and not word.endswith("ss")
        ):
            word = word[:-1]

        return word

    query_words = {
        normalize_word(word)
        for word in (
            user_query
            or ""
        ).split()
    }

    query_words = {
        word
        for word in query_words
        if (
            word
            and len(word) >= 4
            and word not in stop_words
        )
    }

    if not query_words:
        return []

    selected = []

    for chunk in chunks:

        section = (
            chunk.get("section_title")
            or ""
        )

        content = (
            chunk.get("content")
            or ""
        )

        opening = content[:1200]

        section_words = {
            normalize_word(word)
            for word in section.split()
            if normalize_word(word)
        }

        opening_words = {
            normalize_word(word)
            for word in opening.split()
            if normalize_word(word)
        }

        section_overlap = (
            query_words
            & section_words
        )

        opening_overlap = (
            query_words
            & opening_words
        )

        combined_overlap = (
            query_words
            & (
                section_words
                | opening_words
            )
        )

        # Require more than a generic single-word
        # business-domain match whenever the query
        # contains multiple meaningful role words.
        if len(query_words) >= 2:

            if len(combined_overlap) < 2:
                continue

        elif not combined_overlap:
            continue
        
                # A specifically named role section containing
        # additional title modifiers should not become
        # applicable merely because some requested
        # words overlap.
        #
        # Broader collective sections remain eligible
        # through their content.
        if section_overlap:

            title_role_words = {
                word
                for word in section_words
                if (
                    len(word) >= 4
                    and not word.isdigit()
                )
            }

            extra_title_words = (
                title_role_words
                - query_words
            )

            collective_markers = {
                "all",
                "employee",
                "staff",
                "performer",
                "officer",
                "worker",
                "personnel",
                "member",
            }

            is_collective = bool(
                title_role_words
                & collective_markers
            )

            if (
                extra_title_words
                and not is_collective
                and len(section_overlap)
                < len(query_words)
            ):
                continue
            
        if is_distinct_named_role_section(
            section_title=section,
            query_words=query_words,
        ):
            continue

        selected.append(
            (
                len(section_overlap),
                len(opening_overlap),
                chunk,
            )
        )

    selected.sort(
        key=lambda item: (
            -item[0],
            -item[1],
        )
    )

    return [
        item[2]
        for item in selected
    ]
    
def validate_metadata_answer(
    answer: str,
    evidence_chunks: list[dict],
) -> str:
    """
    Validate proposed metadata using field-aware
    evidence grounding.

    A value must occur near an explicit metadata label
    appropriate to that field. Mere occurrence somewhere
    in the document is not sufficient.
    """

    fallback = (
        "Information not found in internal documents"
    )

    fields = (
        "title",
        "document_id",
        "version",
        "effective_date",
        "review_cycle",
        "target_audience",
        "enforcement_level",
        "governance_owner",
    )

    field_labels = {
        "document_id": (
            "document id",
            "document code",
            "policy id",
            "policy code",
            "reference number",
            "reference no",
            "document number",
        ),
        "version": (
            "version",
            "revision",
            "revision number",
            "version number",
        ),
        "effective_date": (
            "effective date",
            "effective from",
            "effective as of",
            "date effective",
        ),
        "review_cycle": (
            "review cycle",
            "review period",
            "review frequency",
            "review interval",
        ),
        "target_audience": (
            "target audience",
            "intended audience",
            "applicable to",
        ),
        "enforcement_level": (
            "enforcement level",
            "compliance level",
        ),
        "governance_owner": (
            "governance owner",
            "document owner",
            "policy owner",
            "owner department",
            "responsible department",
        ),
    }

    try:
        cleaned = (answer or "").strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        proposed = json.loads(cleaned)

        if not isinstance(proposed, dict):
            raise ValueError(
                "Metadata output is not an object."
            )

    except Exception:
        return json.dumps(
            {
                field: fallback
                for field in fields
            },
            indent=2,
        )

    evidence_blocks = []

    for chunk in evidence_chunks:

        content = re.sub(
            r"\s+",
            " ",
            str(
                chunk.get("content")
                or ""
            ),
        ).strip()

        if content:
            evidence_blocks.append(content)

    full_evidence = " ".join(
        evidence_blocks
    ).lower()

    validated = {}

    for field in fields:

        value = proposed.get(field)

        if (
            value is None
            or isinstance(value, (dict, list))
        ):
            validated[field] = fallback
            continue

        value_text = str(value).strip()

        if (
            not value_text
            or value_text.lower()
            == fallback.lower()
        ):
            validated[field] = fallback
            continue

        normalized_value = re.sub(
            r"\s+",
            " ",
            value_text,
        ).strip().lower()

        # ---------------------------------------------
        # TITLE
        # ---------------------------------------------
        # Title is special: document title can be
        # established directly from supplied evidence.
        if field == "title":

            if normalized_value in full_evidence:
                validated[field] = value_text
            else:
                validated[field] = fallback

            continue

        # ---------------------------------------------
        # ALL OTHER METADATA
        # ---------------------------------------------
        labels = field_labels.get(
            field,
            (),
        )

        grounded = False

        for block in evidence_blocks:

            normalized_block = block.lower()

            value_position = (
                normalized_block.find(
                    normalized_value
                )
            )

            if value_position < 0:
                continue

            for label in labels:

                label_position = (
                    normalized_block.find(
                        label
                    )
                )

                if label_position < 0:
                    continue

                # Require metadata label and proposed
                # value to occur locally together.
                distance = abs(
                    value_position
                    - label_position
                )

                if distance <= 160:
                    grounded = True
                    break

            if grounded:
                break

        if grounded:
            validated[field] = value_text
        else:
            validated[field] = fallback

    return json.dumps(
        validated,
        indent=2,
        ensure_ascii=False,
    )
       
def execute_single_document_grc(
    database: Session,
    capability_code: str,
    user_query: str,
    document_query: str,
) -> dict[str, Any]:
    """
    Execute a prepared single-document GRC task.

    This function assumes authorization has already
    occurred before it is called from an API layer.
    """

    prepared = prepare_single_document_grc(
        database=database,
        capability_code=capability_code,
        user_query=user_query,
        document_query=document_query,
    )

    if prepared.get("status") != "ready":
        return {
            **prepared,
            "answer": None,
        }
        
    # ---------------------------------------------------------
    # Procedure mapping is deterministic.
    #
    # The evidence has already been:
    # - document resolved
    # - retrieved
    # - procedure-filtered
    # - section-discovered when necessary
    #
    # Do not send procedure mapping to the LLM because the
    # procedure structure, numbering, and responsible actors
    # must remain grounded in the source document.
    # ---------------------------------------------------------
    if capability_code == "procedure_mapping":

        answer = render_procedure_mapping(
            prepared.get("evidence_chunks", [])
        )

        return {
            "status": "ready",
            "capability": capability_code,
            "document": prepared.get("document"),
            "document_index_id": prepared.get(
                "document_index_id"
            ),
            "answer": answer,
            "evidence_count": prepared.get(
                "evidence_count",
                0,
            ),
        }

    provider = get_ai_provider()

    prompt = prepared["prompt"]
    system_prompt = prepared["system_prompt"]

    # Keep the initial GRC execution bounded.
    # We can tune individual capabilities later
    # using measured results.
    if (
        provider.__class__.__name__
        == "OllamaProvider"
    ):
        tokens = []

        for token in provider.stream(
            prompt=prompt,
            system_prompt=system_prompt,
            num_predict=900,
            num_ctx=8192,
        ):
            tokens.append(token)

        answer = "".join(tokens).strip()

    else:
        answer = (
            provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            or ""
        ).strip()
        
    if capability_code == "metadata_extraction":
        answer = validate_metadata_answer(
            answer=answer,
            evidence_chunks=prepared.get(
                "evidence_chunks",
                [],
            ),
        )

    return {
        **prepared,
        "answer": answer,
    }


def stream_single_document_grc(
    database: Session,
    capability_code: str,
    user_query: str,
    document_query: str,
):
    """
    Stream a single-document GRC response.

    Preparation must succeed before the provider
    is invoked.
    """

    prepared = prepare_single_document_grc(
        database=database,
        capability_code=capability_code,
        user_query=user_query,
        document_query=document_query,
    )

    if prepared.get("status") != "ready":

        status = prepared.get(
            "status",
            "unknown",
        )

        if status == "not_found":
            yield (
                "Information not found in "
                "internal documents."
            )

        elif status == "ambiguous":
            yield (
                "Multiple documents match the request. "
                "Please identify the specific document."
            )

        elif status == "not_indexed":
            yield (
                "The requested document is available "
                "but is not ready for GRC analysis."
            )

        elif status == "no_evidence":
            yield (
                "Information not found in "
                "internal documents."
            )

        else:
            yield (
                "The GRC request could not be prepared."
            )

        return

    provider = get_ai_provider()

    prompt = prepared["prompt"]
    system_prompt = prepared["system_prompt"]

    if (
        provider.__class__.__name__
        == "OllamaProvider"
    ):

        for token in provider.stream(
            prompt=prompt,
            system_prompt=system_prompt,
            num_predict=900,
            num_ctx=8192,
        ):
            yield token

    else:

        answer = provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        if answer:
            yield answer