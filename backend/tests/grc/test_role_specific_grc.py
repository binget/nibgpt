from app.ai.grc_execution_service import (
    classify_role_evidence,
    validate_role_evidence,
)


def make_chunk(
    section_number,
    section_title,
    content,
    page_number=1,
):
    return {
        "section_number": section_number,
        "section_title": section_title,
        "content": content,
        "page_number": page_number,
    }


def test_role_validator_rejects_unrelated_senior_roles():

    chunks = [
        make_chunk(
            "2.1",
            "Chief Credit Officer",
            (
                "The Chief Credit Officer shall approve "
                "specified credit decisions."
            ),
        ),
        make_chunk(
            "2.14",
            "All Credit Performers",
            (
                "All credit performers/lending officers "
                "engaged in the credit process have the "
                "following responsibilities. Each Credit "
                "Performer shall report suspicious credit "
                "transactions."
            ),
        ),
    ]

    selected = validate_role_evidence(
        user_query=(
            "What are the obligations for Credit Officers?"
        ),
        chunks=chunks,
    )

    titles = {
        chunk["section_title"]
        for chunk in selected
    }

    assert "All Credit Performers" in titles
    assert "Chief Credit Officer" not in titles


def test_role_classifier_separates_direct_and_context():

    chunks = [
        make_chunk(
            "2.14",
            "All Credit Performers",
            (
                "All credit performers/lending officers "
                "have the following responsibilities. "
                "Each Credit Performer shall report "
                "suspicious transactions."
            ),
            23,
        ),
        make_chunk(
            "1.4",
            "Objectives",
            (
                "The objective is to provide direction "
                "and guidance for lending officers."
            ),
            12,
        ),
        make_chunk(
            "1.5",
            "Scope of Application",
            (
                "This policy shall govern all "
                "credit-related activities of lending "
                "officers."
            ),
            13,
        ),
    ]

    direct, supporting = classify_role_evidence(
        chunks=chunks,
    )

    direct_sections = {
        chunk["section_number"]
        for chunk in direct
    }

    supporting_sections = {
        chunk["section_number"]
        for chunk in supporting
    }

    assert direct_sections == {"2.14"}
    assert supporting_sections == {"1.4", "1.5"}


def test_scope_shall_does_not_become_role_obligation():

    chunks = [
        make_chunk(
            "1.5",
            "Scope of Application",
            (
                "This Credit Policy shall govern all "
                "credit-related activities of lending "
                "officers."
            ),
        ),
    ]

    direct, supporting = classify_role_evidence(
        chunks=chunks,
    )

    assert direct == []
    assert len(supporting) == 1


def test_objectives_do_not_become_role_obligations():

    chunks = [
        make_chunk(
            "1.4",
            "Objectives",
            (
                "To ensure prudent lending practice. "
                "To support the design of a strong risk "
                "management system."
            ),
        ),
    ]

    direct, supporting = classify_role_evidence(
        chunks=chunks,
    )

    assert direct == []
    assert len(supporting) == 1
