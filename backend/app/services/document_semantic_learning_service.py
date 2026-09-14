import json
import urllib.request
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.document_index import DocumentIndex
from app.services.document_learning_service import (
    normalize_learning_key,
    upsert_document_learning,
)
from app.core.config import settings


SEMANTIC_SYSTEM_PROMPT = """
You are a document semantic-analysis component.

Identify important business concepts ONLY from the supplied
document evidence.

STRICT RULES:

1. Never invent information.
2. Return at most 4 concepts.
3. The concept must appear in the supplied evidence.
4. Concept must be 2 to 8 words.
5. Return at most 2 aliases per concept.
6. Every alias must appear in the supplied evidence.
7. Prefer specific business concepts over generic words.
8. Do not return page numbers.
9. Do not return section names.
10. Do not return evidence quotations.
11. Do not explain anything.
12. Return JSON only.

Required structure:

{
  "concepts": [
    {
      "concept": "business concept",
      "aliases": ["alias"],
      "confidence": 0.90
    }
  ]
}
""".strip()

def generate_semantic_json(
    prompt: str,
    system_prompt: str,
    num_predict: int = 800,
    num_ctx: int = 4096,
) -> dict[str, Any]:

    url = (
        settings.ollama_base_url.rstrip("/")
        + "/api/generate"
    )

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
        "keep_alive": "30m",
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=240,
        ) as response:

            envelope = json.loads(
                response.read().decode("utf-8")
            )

    except Exception as error:
        raise RuntimeError(
            "Unable to generate semantic JSON."
        ) from error

    answer = str(
        envelope.get("response") or ""
    ).strip()
    
    done_reason = str(
        envelope.get("done_reason") or ""
    ).strip()

    if done_reason == "length":
        raise ValueError(
            "Semantic learner output was truncated "
            "by the generation token limit."
        )
        
    eval_count = envelope.get("eval_count")

    if eval_count is not None:
        print(
            "Semantic learner eval_count:",
            eval_count,
            "done_reason:",
            done_reason or "unknown",
        )

    if not answer:
        raise ValueError(
            "Semantic learner returned empty JSON."
        )

    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Semantic learner returned invalid JSON."
        ) from error

    if not isinstance(parsed, dict):
        raise ValueError(
            "Semantic learner JSON must be an object."
        )

    return parsed

def normalize_semantic_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9\s/&_-]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def parse_json_response(
    value: str,
) -> dict[str, Any]:

    if not value:
        raise ValueError(
            "Semantic learner returned an empty response."
        )

    value = value.strip()

    # Remove opening Markdown JSON/code fence.
    value = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Remove closing Markdown fence.
    value = re.sub(
        r"\s*```\s*$",
        "",
        value,
    )

    value = value.strip()

    # First attempt: parse the cleaned response directly.
    try:
        parsed = json.loads(value)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Second attempt:
    # extract the outermost JSON object if the model
    # added any text before or after it.
    start = value.find("{")
    end = value.rfind("}")

    if (
        start >= 0
        and end > start
    ):
        candidate = value[
            start:end + 1
        ].strip()

        try:
            parsed = json.loads(
                candidate
            )

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError as error:
            raise ValueError(
                "Semantic learner returned "
                f"invalid JSON: {error}"
            ) from error

    raise ValueError(
        "Semantic learner returned invalid JSON."
    )


def get_semantic_evidence_chunks(
    database: Session,
    document_index_id: int,
    limit: int = 12,
) -> list[DocumentChunk]:

    return list(
        database.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_index_id
                == document_index_id
            )
            .order_by(
                DocumentChunk.chunk_order.asc()
            )
            .limit(limit)
        ).all()
    )


def build_semantic_evidence(
    chunks: list[DocumentChunk],
    max_chars: int = 6000,
) -> str:

    parts: list[str] = []
    used_chars = 0

    for chunk in chunks:
        section = (
            chunk.section_title
            or "Unknown Section"
        )

        page = (
            chunk.start_page
            or chunk.page_number
            or "Unknown"
        )

        content = (
            chunk.content or ""
        ).strip()

        if not content:
            continue

        block = (
            f"[PAGE {page}]\n"
            f"[SECTION {section}]\n"
            f"{content}\n"
        )

        remaining = (
            max_chars - used_chars
        )

        if remaining <= 0:
            break

        if len(block) > remaining:
            block = block[:remaining]

        parts.append(block)
        used_chars += len(block)

    return "\n".join(parts)


def build_semantic_prompt(
    document: DocumentIndex,
    evidence: str,
) -> str:

    title = (
        document.title
        or document.filename
        or "Unknown Document"
    )

    return f"""
    Document title:
    {title}

    Identify up to 4 important business concepts from the
    document evidence below.

    Return only:
    - concept
    - aliases
    - confidence

    Do not return page numbers, sections, or evidence quotations.

    Prefer:
    - defined business concepts
    - business processes
    - responsibilities or authorities
    - products or services
    - risk concepts
    - abbreviations

    Do not return generic filler concepts.

    DOCUMENT EVIDENCE
    -----------------
    {evidence}
    -----------------

    Return JSON only.
    """.strip()


def phrase_supported_by_evidence(
    phrase: str,
    evidence: str,
) -> bool:

    normalized_phrase = normalize_semantic_text(
        phrase
    )

    normalized_evidence = normalize_semantic_text(
        evidence
    )

    if not normalized_phrase:
        return False

    return (
        normalized_phrase
        in normalized_evidence
    )

def concept_supported_by_evidence_phrase(
    concept: str,
    aliases: list[str],
    evidence_phrase: str,
) -> bool:
    """
    A semantic concept is accepted only when the concept itself
    or one of its aliases appears directly in the evidence phrase.

    This intentionally favors precision over recall.
    """

    normalized_phrase = normalize_semantic_text(
        evidence_phrase
    )

    normalized_concept = normalize_semantic_text(
        concept
    )

    if (
        normalized_concept
        and normalized_concept in normalized_phrase
    ):
        return True

    for alias in aliases:
        normalized_alias = normalize_semantic_text(
            alias
        )

        if (
            normalized_alias
            and normalized_alias in normalized_phrase
        ):
            return True

    return False

def find_phrase_in_chunk(
    phrase: str,
    content: str,
) -> tuple[int, int] | None:
    """
    Find a phrase in chunk content using case-insensitive,
    whitespace-tolerant matching.
    """

    phrase = (phrase or "").strip()

    if not phrase or not content:
        return None

    words = phrase.split()

    if not words:
        return None

    pattern = r"\s+".join(
        re.escape(word)
        for word in words
    )

    match = re.search(
        pattern,
        content,
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    return (
        match.start(),
        match.end(),
    )


def extract_grounded_evidence(
    content: str,
    start: int,
    end: int,
    max_chars: int = 240,
) -> str:
    """
    Return a short piece of actual document text surrounding
    the matched concept.
    """

    if not content:
        return ""

    left = max(
        0,
        start - 80,
    )

    right = min(
        len(content),
        end + 160,
    )

    evidence = content[
        left:right
    ].strip()

    evidence = re.sub(
        r"\s+",
        " ",
        evidence,
    )

    if len(evidence) > max_chars:
        evidence = evidence[:max_chars].rstrip()

    return evidence


def score_grounding_candidate(
    chunk: DocumentChunk,
    evidence_phrase: str,
) -> float:
    """
    Score a grounding candidate so cleaner, more meaningful
    occurrences are preferred over noisy OCR/cover-page text.
    """

    score = 0.0

    section = (
        chunk.section_title
        or ""
    ).strip()

    # Prefer chunks that actually have a section.
    if section:
        score += 1.0

    # Penalize generic/noisy structural sections.
    if section.lower() not in {
        "document introduction",
        "unknown section",
    }:
        score += 1.0

    if evidence_phrase:
        total_length = len(
            evidence_phrase
        )

        letters = sum(
            char.isalpha()
            for char in evidence_phrase
        )

        symbols = sum(
            not char.isalnum()
            and not char.isspace()
            for char in evidence_phrase
        )

        if total_length > 0:
            letter_ratio = (
                letters
                / total_length
            )

            symbol_ratio = (
                symbols
                / total_length
            )

            score += (
                letter_ratio
                * 2.0
            )

            score -= (
                symbol_ratio
                * 2.0
            )

    return score


def find_concept_grounding(
    concept: str,
    aliases: list[str],
    chunks: list[DocumentChunk],
) -> dict[str, Any] | None:
    """
    Ground a proposed semantic concept against actual indexed
    document chunks.

    All occurrences are evaluated and the cleanest grounding
    candidate is returned.

    Page, section and evidence always come from the database,
    never from the LLM.
    """

    candidates = [
        concept,
        *aliases,
    ]

    seen_candidates: set[str] = set()

    grounding_candidates: list[
        dict[str, Any]
    ] = []

    for candidate in candidates:

        candidate = str(
            candidate or ""
        ).strip()

        candidate_key = normalize_learning_key(
            candidate
        )

        if (
            not candidate_key
            or candidate_key
            in seen_candidates
        ):
            continue

        seen_candidates.add(
            candidate_key
        )

        for chunk in chunks:

            content = (
                chunk.content
                or ""
            )

            if not content:
                continue

            match = find_phrase_in_chunk(
                candidate,
                content,
            )

            if match is None:
                continue

            start, end = match

            evidence_phrase = (
                extract_grounded_evidence(
                    content,
                    start,
                    end,
                )
            )

            if not evidence_phrase:
                continue

            page = (
                chunk.start_page
                or chunk.page_number
            )

            score = (
                score_grounding_candidate(
                    chunk,
                    evidence_phrase,
                )
            )
            
            # Prefer an exact occurrence of the canonical concept
            # over an alias when both are available.
            if (
                normalize_learning_key(candidate)
                == normalize_learning_key(concept)
            ):
                score += 2.0

            grounding_candidates.append({
                "matched_phrase":
                    candidate,

                "evidence_phrase":
                    evidence_phrase,

                "section":
                    chunk.section_title,

                "page":
                    page,

                "chunk_id":
                    chunk.id,

                "_score":
                    score,
            })

    if not grounding_candidates:
        return None

    best_candidate = max(
        grounding_candidates,
        key=lambda item: item[
            "_score"
        ],
    )

    best_candidate.pop(
        "_score",
        None,
    )

    return best_candidate

def validate_semantic_concepts(
    payload: dict[str, Any],
    chunks: list[DocumentChunk],
) -> list[dict[str, Any]]:

    raw_concepts = payload.get(
        "concepts"
    )

    if not isinstance(
        raw_concepts,
        list,
    ):
        return []

    validated: list[
        dict[str, Any]
    ] = []

    seen_concepts: set[str] = set()

    for item in raw_concepts:

        if not isinstance(
            item,
            dict,
        ):
            continue

        concept = str(
            item.get("concept")
            or ""
        ).strip()

        if not concept:
            continue

        concept_key = normalize_learning_key(
            concept
        )

        if (
            not concept_key
            or concept_key in seen_concepts
        ):
            continue

        # Keep concepts reasonably specific.
        word_count = len(
            concept.split()
        )

        if (
            word_count < 2
            or word_count > 8
        ):
            continue

        aliases = item.get(
            "aliases",
            []
        )

        if not isinstance(
            aliases,
            list,
        ):
            aliases = []

        aliases = [
            str(alias).strip()
            for alias in aliases[:2]
            if str(alias).strip()
        ]

        try:
            confidence = float(
                item.get(
                    "confidence",
                    0.70,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            confidence = 0.70

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        if confidence < 0.65:
            continue

        grounding = find_concept_grounding(
            concept=concept,
            aliases=aliases,
            chunks=chunks,
        )

        if grounding is None:
            continue

        #
        # Validate aliases independently.
        # An alias is kept only if it actually appears
        # somewhere in this document.
        #
        validated_aliases = []

        for alias in aliases:

            alias_grounding = (
                find_concept_grounding(
                    concept=alias,
                    aliases=[],
                    chunks=chunks,
                )
            )

            if alias_grounding is None:
                continue

            alias_key = (
                normalize_learning_key(
                    alias
                )
            )

            if (
                alias_key
                and alias_key != concept_key
                and alias_key
                not in {
                    normalize_learning_key(
                        value
                    )
                    for value
                    in validated_aliases
                }
            ):
                validated_aliases.append(
                    alias
                )

        seen_concepts.add(
            concept_key
        )

        validated.append({
            "concept":
                concept,

            "concept_key":
                concept_key,

            "aliases":
                validated_aliases,

            "matched_phrase":
                grounding[
                    "matched_phrase"
                ],

            "evidence_phrase":
                grounding[
                    "evidence_phrase"
                ],

            "section":
                grounding[
                    "section"
                ],

            "page":
                grounding[
                    "page"
                ],

            "chunk_id":
                grounding[
                    "chunk_id"
                ],

            "confidence":
                confidence,
        })

    return validated


def propose_document_semantics(
    database: Session,
    document_index_id: int,
) -> dict[str, Any]:

    document = database.get(
        DocumentIndex,
        document_index_id,
    )

    if document is None:
        raise ValueError(
            "Document index was not found."
        )

    chunks = get_semantic_evidence_chunks(
        database,
        document_index_id,
    )

    if not chunks:
        raise ValueError(
            "Document has no indexed chunks."
        )

    evidence = build_semantic_evidence(
        chunks
    )

    if not evidence:
        raise ValueError(
            "Document has no usable semantic evidence."
        )

    payload = generate_semantic_json(
        prompt=build_semantic_prompt(
            document,
            evidence,
        ),
        system_prompt=SEMANTIC_SYSTEM_PROMPT,
        num_predict=800,
        num_ctx=4096,
    )

    concepts = validate_semantic_concepts(
        payload,
        chunks,
    )

    return {
        "document_index_id": (
            document.id
        ),
        "document_title": (
            document.title
            or document.filename
        ),
        "evidence_chunk_count": (
            len(chunks)
        ),
        "validated_concept_count": (
            len(concepts)
        ),
        "concepts": concepts,
    }
    
def score_grounding_candidate(
    chunk: DocumentChunk,
    evidence_phrase: str,
) -> float:
    score = 0.0

    section = (
        chunk.section_title
        or ""
    ).strip()

    if section:
        score += 1.0

    if section.lower() not in {
        "document introduction",
        "unknown section",
    }:
        score += 1.0

    letters = sum(
        char.isalpha()
        for char in evidence_phrase
    )

    symbols = sum(
        not char.isalnum()
        and not char.isspace()
        for char in evidence_phrase
    )

    if evidence_phrase:
        letter_ratio = (
            letters
            / len(evidence_phrase)
        )

        symbol_ratio = (
            symbols
            / len(evidence_phrase)
        )

        score += letter_ratio * 2.0
        score -= symbol_ratio * 2.0

    return score

def persist_validated_document_semantics(
    database: Session,
    document_index_id: int,
    concepts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Persist only already-validated semantic concepts and aliases.

    No model output is written directly to the learning catalog.
    """

    concept_count = 0
    alias_count = 0

    for item in concepts:
        concept = str(
            item.get("concept")
            or ""
        ).strip()

        concept_key = str(
            item.get("concept_key")
            or ""
        ).strip()

        if not concept or not concept_key:
            continue

        confidence = float(
            item.get(
                "confidence",
                0.70,
            )
        )

        source_page = item.get(
            "page"
        )

        source_section = item.get(
            "section"
        )

        evidence_phrase = str(
            item.get(
                "evidence_phrase",
                "",
            )
            or ""
        ).strip()

        upsert_document_learning(
            database=database,
            document_index_id=document_index_id,
            learning_type="concept",
            learning_key=concept_key,
            learning_value=evidence_phrase or concept,
            confidence=confidence,
            source_page=source_page,
            source_section=source_section,
            learned_by="semantic_validated",
        )

        concept_count += 1

        aliases = item.get(
            "aliases",
            []
        )

        if not isinstance(
            aliases,
            list,
        ):
            aliases = []

        for alias in aliases:
            alias = str(
                alias
                or ""
            ).strip()

            if not alias:
                continue

            alias_key = (
                normalize_learning_key(
                    alias
                )
            )

            if (
                not alias_key
                or alias_key
                == concept_key
            ):
                continue

            upsert_document_learning(
                database=database,
                document_index_id=document_index_id,
                learning_type="alias",
                learning_key=alias_key,
                learning_value=concept,
                confidence=confidence,
                source_page=source_page,
                source_section=source_section,
                learned_by="semantic_validated",
            )

            alias_count += 1

    database.commit()

    return {
        "document_index_id":
            document_index_id,

        "concept_records":
            concept_count,

        "alias_records":
            alias_count,

        "total_records":
            concept_count
            + alias_count,
    }
    
def learn_document_semantics(
    database: Session,
    document_index_id: int,
    persist: bool = False,
) -> dict[str, Any]:
    """
    Run the complete semantic-learning pipeline.

    Flow:
        document
        -> evidence
        -> LLM proposals
        -> deterministic grounding
        -> optional persistence

    Persistence is OFF by default so new document types can
    be inspected before adding knowledge to the catalog.
    """

    proposal = propose_document_semantics(
        database=database,
        document_index_id=document_index_id,
    )

    concepts = proposal.get(
        "concepts",
        [],
    )

    result: dict[str, Any] = {
        "document_index_id":
            proposal["document_index_id"],

        "document_title":
            proposal["document_title"],

        "evidence_chunk_count":
            proposal["evidence_chunk_count"],

        "validated_concept_count":
            len(concepts),

        "concepts":
            concepts,

        "persisted":
            False,
    }

    if not persist:
        return result

    persistence = (
        persist_validated_document_semantics(
            database=database,
            document_index_id=document_index_id,
            concepts=concepts,
        )
    )

    result["persisted"] = True
    result["persistence"] = persistence

    return result
