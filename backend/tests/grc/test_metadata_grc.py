import json

from app.ai.grc_execution_service import (
    validate_metadata_answer,
)


FALLBACK = (
    "Information not found in internal documents"
)


def test_rejects_ungrounded_metadata():

    answer = """
    {
      "title": "Credit Policy",
      "document_id": "123456789",
      "version": "1.0",
      "effective_date": "2025-01-01",
      "review_cycle": "Annual",
      "target_audience": "All Employees",
      "enforcement_level": "Strict",
      "governance_owner": "Board of Directors"
    }
    """

    chunks = [
        {
            "content": (
                "Credit Policy. This document establishes "
                "credit governance requirements."
            )
        }
    ]

    result = json.loads(
        validate_metadata_answer(
            answer=answer,
            evidence_chunks=chunks,
        )
    )

    assert result["title"] == "Credit Policy"

    for field in (
        "document_id",
        "version",
        "effective_date",
        "review_cycle",
        "target_audience",
        "enforcement_level",
        "governance_owner",
    ):
        assert result[field] == FALLBACK


def test_random_occurrence_does_not_validate_field():

    answer = """
    {
      "title": "Credit Policy",
      "document_id": "Credit Policy",
      "version": "1.0",
      "effective_date": "2023-01-01",
      "review_cycle": "Annual",
      "target_audience": "Employees",
      "enforcement_level": "Strict",
      "governance_owner": "Board"
    }
    """

    chunks = [
        {
            "content": (
                "Credit Policy. Annual reporting is "
                "required. Strict controls apply. "
                "The Board receives reports."
            )
        }
    ]

    result = json.loads(
        validate_metadata_answer(
            answer=answer,
            evidence_chunks=chunks,
        )
    )

    assert result["document_id"] == FALLBACK
    assert result["review_cycle"] == FALLBACK
    assert result["enforcement_level"] == FALLBACK
    assert result["governance_owner"] == FALLBACK


def test_accepts_explicitly_labeled_metadata():

    answer = """
    {
      "title": "Credit Policy",
      "document_id": "CP-001",
      "version": "2.1",
      "effective_date": "01 April 2026",
      "review_cycle": "Annual",
      "target_audience": "Information not found in internal documents",
      "enforcement_level": "Information not found in internal documents",
      "governance_owner": "Credit Risk Department"
    }
    """

    chunks = [
        {
            "content": (
                "Credit Policy. "
                "Document ID: CP-001. "
                "Version: 2.1. "
                "Effective Date: 01 April 2026. "
                "Review Cycle: Annual. "
                "Document Owner: Credit Risk Department."
            )
        }
    ]

    result = json.loads(
        validate_metadata_answer(
            answer=answer,
            evidence_chunks=chunks,
        )
    )

    assert result["title"] == "Credit Policy"
    assert result["document_id"] == "CP-001"
    assert result["version"] == "2.1"
    assert result["effective_date"] == "01 April 2026"
    assert result["review_cycle"] == "Annual"
    assert result["governance_owner"] == "Credit Risk Department"
