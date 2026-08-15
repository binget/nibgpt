from sqlalchemy.orm import Session

from app.ai.entity_extractor import extract_entities
from app.ai.intent_detector import detect_intent
from app.ai.metadata_resolver import resolve_metadata


def calculate_overall_confidence(
    intent_confidence: int,
    metadata_confidence: int,
    is_safe: bool,
) -> int:
    if not is_safe:
        return 0

    if metadata_confidence == 0:
        return round(intent_confidence * 0.35)

    return round(
        (intent_confidence * 0.35)
        + (metadata_confidence * 0.65)
    )


def analyze_prompt_pipeline(
    database: Session,
    prompt: str,
    data_source_id: int | None = None,
    maximum_results: int = 5,
) -> dict:
    intent_result = detect_intent(prompt)
    extraction_result = extract_entities(prompt)

    warnings: list[str] = []
    explanation: list[str] = []

    if not intent_result.is_safe:
        warnings.append(
            intent_result.blocked_reason
            or "The prompt violates the read-only safety policy."
        )

        return {
            "prompt": prompt,
            "normalized_prompt": extraction_result["normalized_prompt"],
            "intent": intent_result.intent,
            "intent_confidence": intent_result.confidence,
            "entities": extraction_result["entities"],
            "keywords": extraction_result["keywords"],
            "time_expressions": extraction_result["time_expressions"],
            "status_terms": extraction_result["status_terms"],
            "aggregation_terms": extraction_result["aggregation_terms"],
            "is_safe": False,
            "blocked_reason": intent_result.blocked_reason,
            "metadata_confidence": 0,
            "overall_confidence": 0,
            "matched_tables": [],
            "warnings": warnings,
            "explanation": [
                "The request was blocked before metadata resolution."
            ],
        }

    metadata_matches = resolve_metadata(
        database=database,
        prompt=prompt,
        keywords=extraction_result["keywords"],
        data_source_id=data_source_id,
        maximum_results=maximum_results,
    )

    metadata_confidence = (
        metadata_matches[0].confidence
        if metadata_matches
        else 0
    )

    overall_confidence = calculate_overall_confidence(
        intent_confidence=intent_result.confidence,
        metadata_confidence=metadata_confidence,
        is_safe=intent_result.is_safe,
    )

    if intent_result.intent == "unknown":
        warnings.append(
            "NIBGPT could not determine the reporting intent with high confidence."
        )

    if not extraction_result["keywords"]:
        warnings.append(
            "No meaningful business terms were extracted."
        )

    if not metadata_matches:
        warnings.append(
            "No matching approved metadata was found."
        )
    elif metadata_confidence < 70:
        warnings.append(
            "The metadata match has low confidence and requires clarification."
        )

    if intent_result.matched_phrases:
        explanation.append(
            "Intent detected from: "
            + ", ".join(intent_result.matched_phrases)
        )

    if extraction_result["time_expressions"]:
        explanation.append(
            "Time expressions detected: "
            + ", ".join(
                extraction_result["time_expressions"]
            )
        )

    if extraction_result["status_terms"]:
        explanation.append(
            "Status terms detected: "
            + ", ".join(
                extraction_result["status_terms"]
            )
        )

    if metadata_matches:
        strongest = metadata_matches[0]

        explanation.append(
            "Strongest table match: "
            + (
                strongest.table.business_name
                or strongest.table.table_name
            )
            + f" ({strongest.confidence}% confidence)"
        )

    return {
        "prompt": prompt,
        "normalized_prompt": extraction_result["normalized_prompt"],
        "intent": intent_result.intent,
        "intent_confidence": intent_result.confidence,
        "entities": extraction_result["entities"],
        "keywords": extraction_result["keywords"],
        "time_expressions": extraction_result["time_expressions"],
        "status_terms": extraction_result["status_terms"],
        "aggregation_terms": extraction_result["aggregation_terms"],
        "is_safe": intent_result.is_safe,
        "blocked_reason": intent_result.blocked_reason,
        "metadata_confidence": metadata_confidence,
        "overall_confidence": overall_confidence,
        "matched_tables": metadata_matches,
        "warnings": warnings,
        "explanation": explanation,
    }