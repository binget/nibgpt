import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_learning import DocumentLearning


MAX_MATCHES = 6
MAX_EXPANDED_TERMS = 8


def normalize_query_text(
    value: str | None,
) -> str:
    """
    Normalize text for conservative learning-catalog matching.
    """

    if not value:
        return ""

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9\s/&(),_-]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def learning_key_in_query(
    learning_key: str,
    normalized_query: str,
) -> bool:
    """
    Match a learned key as a phrase/token sequence rather than
    using unrestricted substring matching.
    """

    key = normalize_query_text(
        learning_key
    )

    if not key or not normalized_query:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(key).replace(
            r"\ ",
            r"\s+",
        )
        + r"(?![a-z0-9])"
    )

    return bool(
        re.search(
            pattern,
            normalized_query,
            flags=re.IGNORECASE,
        )
    )


def find_query_learning_matches(
    database: Session,
    query: str,
    document_index_id: int | None = None,
    limit: int = MAX_MATCHES,
) -> list[DocumentLearning]:
    """
    Find validated learned concepts/aliases explicitly present
    in the user's query.

    This function does not perform document retrieval and does
    not change authorization.
    """

    normalized_query = normalize_query_text(
        query
    )

    if not normalized_query:
        return []

    statement = (
        select(DocumentLearning)
        .where(
            DocumentLearning.learning_type.in_(
                [
                    "concept",
                    "alias",
                ]
            ),
            DocumentLearning.learned_by
            == "semantic_validated",
            DocumentLearning.confidence
            >= 0.65,
        )
        .order_by(
            DocumentLearning.confidence.desc(),
            DocumentLearning.learning_type.asc(),
            DocumentLearning.learning_key.asc(),
        )
    )

    if document_index_id is not None:
        statement = statement.where(
            DocumentLearning.document_index_id
            == document_index_id
        )

    rows = list(
        database.scalars(
            statement
        ).all()
    )

    matches = []

    for row in rows:

        if not learning_key_in_query(
            row.learning_key,
            normalized_query,
        ):
            continue

        matches.append(
            row
        )

        if len(matches) >= limit:
            break

    return matches


def build_document_learning_query(
    database: Session,
    query: str,
    document_index_id: int | None = None,
) -> dict[str, Any]:
    """
    Enrich a query using only validated learning-catalog records.

    Original user text is always preserved.

    Alias:
        learning_key   = alias
        learning_value = canonical concept

    Concept:
        learning_key   = canonical concept
    """

    original_query = (
        query
        or ""
    ).strip()

    matches = find_query_learning_matches(
        database=database,
        query=original_query,
        document_index_id=document_index_id,
    )

    expanded_terms: list[str] = []
    seen_terms: set[str] = set()

    match_details = []

    for row in matches:

        terms = []

        if row.learning_type == "alias":

            canonical = (
                row.learning_value
                or ""
            ).strip()

            if canonical:
                terms.append(
                    canonical
                )

        elif row.learning_type == "concept":

            concept = (
                row.learning_key
                or ""
            ).strip()

            if concept:
                terms.append(
                    concept
                )

        accepted_terms = []

        for term in terms:

            normalized_term = (
                normalize_query_text(
                    term
                )
            )

            if (
                not normalized_term
                or normalized_term
                in seen_terms
            ):
                continue

            # Do not redundantly append a term already
            # explicitly present in the user's query.
            if learning_key_in_query(
                term,
                normalize_query_text(
                    original_query
                ),
            ):
                continue

            seen_terms.add(
                normalized_term
            )

            expanded_terms.append(
                term
            )

            accepted_terms.append(
                term
            )

            if (
                len(expanded_terms)
                >= MAX_EXPANDED_TERMS
            ):
                break

        match_details.append({
            "document_index_id":
                row.document_index_id,

            "learning_type":
                row.learning_type,

            "matched_key":
                row.learning_key,

            "learning_value":
                row.learning_value,

            "confidence":
                row.confidence,

            "expanded_terms":
                accepted_terms,
        })

        if (
            len(expanded_terms)
            >= MAX_EXPANDED_TERMS
        ):
            break

    if expanded_terms:

        enriched_query = (
            original_query
            + " "
            + " ".join(
                expanded_terms
            )
        ).strip()

    else:
        enriched_query = (
            original_query
        )

    return {
        "original_query":
            original_query,

        "enriched_query":
            enriched_query,

        "was_enriched":
            enriched_query
            != original_query,

        "expanded_terms":
            expanded_terms,

        "matches":
            match_details,
    }
    
def discover_documents_from_learning(
    database: Session,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Discover candidate indexed documents from validated
    semantic learning records.

    Alias and canonical concept matches belonging to the same
    concept are counted once per document.

    This does NOT retrieve document content and does NOT
    bypass authorization.
    """

    matches = find_query_learning_matches(
        database=database,
        query=query,
        document_index_id=None,
        limit=20,
    )

    if not matches:
        return []

    candidates: dict[int, dict[str, Any]] = {}

    for row in matches:

        document_id = (
            row.document_index_id
        )

        if document_id not in candidates:

            candidates[document_id] = {
                "document_index_id":
                    document_id,

                "score":
                    0.0,

                "matches":
                    [],

                "_semantic_keys":
                    set(),
            }

        # ---------------------------------------------
        # Resolve one canonical semantic identity.
        #
        # Alias:
        #   value contains canonical concept.
        #
        # Concept:
        #   key itself is canonical concept.
        # ---------------------------------------------

        if row.learning_type == "alias":

            semantic_key = normalize_query_text(
                row.learning_value
                or row.learning_key
            )

            type_score = 2.0

        else:

            semantic_key = normalize_query_text(
                row.learning_key
            )

            type_score = 1.5

        if not semantic_key:
            continue

        confidence = float(
            row.confidence
            or 0.0
        )

        already_counted = (
            semantic_key
            in candidates[
                document_id
            ]["_semantic_keys"]
        )

        # ---------------------------------------------
        # Keep all matching evidence for diagnostics,
        # but score one semantic concept only once.
        # ---------------------------------------------

        candidates[
            document_id
        ]["matches"].append({
            "learning_type":
                row.learning_type,

            "matched_key":
                row.learning_key,

            "learning_value":
                row.learning_value,

            "semantic_key":
                semantic_key,

            "confidence":
                confidence,

            "scored":
                not already_counted,
        })

        if already_counted:
            continue

        candidates[
            document_id
        ]["_semantic_keys"].add(
            semantic_key
        )

        candidates[
            document_id
        ]["score"] += (
            type_score
            + confidence
        )

    ranked = sorted(
        candidates.values(),
        key=lambda item: (
            -item["score"],
            item["document_index_id"],
        ),
    )

    result = []

    for item in ranked[:limit]:

        result.append({
            "document_index_id":
                item["document_index_id"],

            "score":
                round(
                    item["score"],
                    4,
                ),

            "matches":
                item["matches"],
        })

    return result
