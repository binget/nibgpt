import re
from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.document_learning import DocumentLearning
from app.models.document_index import DocumentIndex


LEARNING_TYPE_DOCUMENT_TYPE = "document_type"
LEARNING_TYPE_TOPIC = "topic"
LEARNING_TYPE_TERM = "term"
LEARNING_TYPE_SECTION_PATTERN = "section_pattern"


DOCUMENT_TYPE_PATTERNS = {
    "policy": (
        "policy",
        "policies",
    ),
    "procedure": (
        "procedure",
        "procedures",
    ),
    "manual": (
        "manual",
        "user manual",
    ),
    "guideline": (
        "guideline",
        "guidelines",
    ),
    "directive": (
        "directive",
        "directives",
    ),
    "circular": (
        "circular",
    ),
    "strategy": (
        "strategy",
        "strategic plan",
    ),
    "report": (
        "report",
        "annual report",
    ),
}


STOP_WORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "been",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "more",
    "must",
    "only",
    "other",
    "shall",
    "should",
    "such",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "using",
    "were",
    "where",
    "which",
    "will",
    "with",
    "would",
    "based",
    "ensure",
    "ensures",
    "means",
    "team",
    "including",
    "include",
    "includes",
    "provide",
    "provides",
    "provided",
    "within",
    "upon",
    "thereof",
    "therein",
    "hereby",
    "herein",
    "amended",
    "potential",
    "service",
    "services",
    "without",
}


def normalize_learning_key(
    value: str,
) -> str:
    value = value.strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value

def clean_section_title(
    value: str,
) -> str:
    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    value = re.sub(
        r"[\s:;,*‘’'\"|]+$",
        "",
        value,
    )

    return value.strip()


def is_meaningful_section_title(
    value: str,
) -> bool:
    title = clean_section_title(value)

    if not title:
        return False

    if len(title) < 2:
        return False

    if len(title) > 120:
        return False

    words = re.findall(
        r"[A-Za-z0-9&/-]+",
        title,
    )

    if not words:
        return False

    # Long sentences incorrectly detected as headings
    # should not become learned structure.
    if len(words) > 12:
        return False

    alpha_words = [
        word
        for word in words
        if re.search(r"[A-Za-z]", word)
    ]

    if not alpha_words:
        return False

    return True

def upsert_document_learning(
    database: Session,
    *,
    document_index_id: int,
    learning_type: str,
    learning_key: str,
    learning_value: str,
    confidence: float = 1.0,
    source_page: int | None = None,
    source_section: str | None = None,
    learned_by: str = "automatic",
) -> DocumentLearning:

    normalized_key = normalize_learning_key(
        learning_key
    )

    statement = (
        select(DocumentLearning)
        .where(
            DocumentLearning.document_index_id
            == document_index_id,
            DocumentLearning.learning_type
            == learning_type,
            DocumentLearning.learning_key
            == normalized_key,
        )
    )

    learning = database.scalar(statement)

    if learning is None:
        learning = DocumentLearning(
            document_index_id=document_index_id,
            learning_type=learning_type,
            learning_key=normalized_key,
            learning_value=learning_value,
            confidence=max(
                0.0,
                min(1.0, confidence),
            ),
            source_page=source_page,
            source_section=source_section,
            learned_by=learned_by,
        )

        database.add(learning)

    else:
        learning.learning_value = learning_value
        learning.confidence = max(
            learning.confidence,
            max(0.0, min(1.0, confidence)),
        )

        if (
            learning.source_page is None
            and source_page is not None
        ):
            learning.source_page = source_page

        if (
            not learning.source_section
            and source_section
        ):
            learning.source_section = (
                source_section
            )

    return learning


def detect_document_type(
    document: DocumentIndex,
    chunks: list[DocumentChunk],
) -> tuple[str | None, float]:

    candidates = [
        document.title or "",
        document.filename or "",
    ]

    for chunk in chunks[:8]:
        candidates.append(
            chunk.section_title or ""
        )

        candidates.append(
            chunk.content[:800]
        )

    text = " ".join(candidates).lower()

    scores: Counter[str] = Counter()

    for document_type, patterns in (
        DOCUMENT_TYPE_PATTERNS.items()
    ):
        for pattern in patterns:
            if pattern in text:
                scores[document_type] += 1

    if not scores:
        return None, 0.0

    best_type, score = scores.most_common(1)[0]

    confidence = min(
        0.95,
        0.60 + (score * 0.08),
    )

    return best_type, confidence


def learn_section_patterns(
    database: Session,
    document: DocumentIndex,
    chunks: list[DocumentChunk],
) -> int:

    learned = 0
    seen: set[str] = set()

    for chunk in chunks:
        raw_title = (
            chunk.section_title or ""
        ).strip()

        if not is_meaningful_section_title(
            raw_title
        ):
            continue

        title = clean_section_title(
            raw_title
        )

        key = normalize_learning_key(
            title
        )

        if not key or key in seen:
            continue

        seen.add(key)

        upsert_document_learning(
            database,
            document_index_id=document.id,
            learning_type=(
                LEARNING_TYPE_SECTION_PATTERN
            ),
            learning_key=key,
            learning_value=title,
            confidence=0.90,
            source_page=(
                chunk.start_page
                or chunk.page_number
            ),
            source_section=title,
        )

        learned += 1

    return learned


def normalize_candidate_term(
    word: str,
) -> str:
    word = word.lower().strip()

    # Conservative plural normalization.
    if (
        len(word) > 4
        and word.endswith("s")
        and not word.endswith(
            ("ss", "us", "is")
        )
    ):
        word = word[:-1]

    return word


def extract_candidate_terms(
    chunks: list[DocumentChunk],
    limit: int = 30,
) -> list[tuple[str, int, int]]:

    total_frequency: Counter[str] = Counter()
    chunk_frequency: Counter[str] = Counter()

    for chunk in chunks:
        text = (
            (chunk.section_title or "")
            + " "
            + chunk.content
        ).lower()

        raw_words = re.findall(
            r"[a-z][a-z0-9_-]{3,}",
            text,
        )

        chunk_terms: set[str] = set()

        for raw_word in raw_words:
            word = normalize_candidate_term(
                raw_word
            )

            if len(word) < 4:
                continue

            if word in STOP_WORDS:
                continue

            if word.isdigit():
                continue

            total_frequency[word] += 1
            chunk_terms.add(word)

        for term in chunk_terms:
            chunk_frequency[term] += 1

    ranked = sorted(
        total_frequency.items(),
        key=lambda item: (
            chunk_frequency[item[0]],
            item[1],
        ),
        reverse=True,
    )

    return [
        (
            term,
            frequency,
            chunk_frequency[term],
        )
        for term, frequency in ranked[:limit]
    ]


def learn_terms(
    database: Session,
    document: DocumentIndex,
    chunks: list[DocumentChunk],
) -> int:

    candidates = extract_candidate_terms(
        chunks
    )

    if not candidates:
        return 0

    highest_frequency = max(
        frequency
        for _, frequency, _ in candidates
    )

    total_chunks = max(
        len(chunks),
        1,
    )

    learned = 0

    for (
        term,
        frequency,
        chunk_count,
    ) in candidates:

        if frequency < 3:
            continue

        chunk_ratio = (
            chunk_count / total_chunks
        )

        # A word appearing almost everywhere is often
        # document boilerplate rather than a useful concept.
        if chunk_ratio > 0.85:
            continue

        frequency_score = min(
            1.0,
            frequency
            / max(highest_frequency, 1),
        )

        coverage_score = min(
            1.0,
            chunk_count
            / max(total_chunks * 0.35, 1),
        )

        confidence = min(
            0.92,
            0.50
            + frequency_score * 0.22
            + coverage_score * 0.18,
        )

        upsert_document_learning(
            database,
            document_index_id=document.id,
            learning_type=LEARNING_TYPE_TERM,
            learning_key=term,
            learning_value=term,
            confidence=confidence,
        )

        learned += 1

    return learned


def learn_document(
    database: Session,
    document_index_id: int,
    *,
    replace_automatic: bool = True,
) -> dict:

    document = database.get(
        DocumentIndex,
        document_index_id,
    )

    if document is None:
        raise ValueError(
            "Document index was not found."
        )

    chunks = list(
        database.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_index_id
                == document_index_id
            )
            .order_by(
                DocumentChunk.chunk_order.asc()
            )
        ).all()
    )

    if not chunks:
        raise ValueError(
            "Document has no indexed chunks."
        )

    if replace_automatic:
        database.execute(
            delete(DocumentLearning)
            .where(
                DocumentLearning.document_index_id
                == document_index_id,
                DocumentLearning.learned_by
                == "automatic",
            )
        )

    document_type, type_confidence = (
        detect_document_type(
            document,
            chunks,
        )
    )

    learned_type = 0

    if document_type:
        upsert_document_learning(
            database,
            document_index_id=document.id,
            learning_type=(
                LEARNING_TYPE_DOCUMENT_TYPE
            ),
            learning_key=document_type,
            learning_value=document_type,
            confidence=type_confidence,
        )

        learned_type = 1

    section_count = learn_section_patterns(
        database,
        document,
        chunks,
    )

    term_count = learn_terms(
        database,
        document,
        chunks,
    )

    database.commit()

    return {
        "document_index_id": document.id,
        "document_title": (
            document.title
            or document.filename
        ),
        "document_type": document_type,
        "document_type_confidence": (
            type_confidence
        ),
        "learned": {
            "document_type": learned_type,
            "section_patterns": section_count,
            "terms": term_count,
        },
        "total_learning_records": (
            learned_type
            + section_count
            + term_count
        ),
    }


def get_document_learning(
    database: Session,
    document_index_id: int,
) -> list[DocumentLearning]:

    return list(
        database.scalars(
            select(DocumentLearning)
            .where(
                DocumentLearning.document_index_id
                == document_index_id
            )
            .order_by(
                DocumentLearning.learning_type.asc(),
                DocumentLearning.confidence.desc(),
            )
        ).all()
    )
