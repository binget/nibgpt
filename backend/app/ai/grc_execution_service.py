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