from app.ai.grc_execution_service import (
    extract_numbered_procedure_items,
    extract_explicit_procedure_roles,
)


def test_extracts_numbered_procedure_items():
    chunks = [
        {
            "section_title": "Example Processing",
            "page_number": 10,
            "clause_id": None,
            "content": """
4.1. Example Processing
1. The process shall begin with submission.
2.The request shall be reviewed.
3.The request shall be approved.
4.A decision shall be communicated.
""",
        }
    ]

    result = extract_numbered_procedure_items(chunks)

    assert len(result) == 1
    assert len(result[0]["items"]) == 4

    assert [
        item["number"]
        for item in result[0]["items"]
    ] == [1, 2, 3, 4]


def test_numbered_section_heading_is_not_a_step():
    chunks = [
        {
            "section_title": "Decision Execution",
            "page_number": 20,
            "clause_id": None,
            "content": """
7. DECISION EXECUTION
1. The decision shall be communicated.
2. The customer may submit an appeal.
3. The appeal shall be reviewed.
""",
        }
    ]

    result = extract_numbered_procedure_items(chunks)

    assert len(result) == 1

    numbers = [
        item["number"]
        for item in result[0]["items"]
    ]

    assert numbers == [1, 2, 3]
    assert 7 not in numbers


def test_decimal_section_number_is_not_a_step():
    chunks = [
        {
            "section_title": "Request Processing",
            "page_number": 30,
            "clause_id": None,
            "content": """
4.1. Request Processing
1. The request shall be submitted.
2. The request shall be reviewed.
""",
        }
    ]

    result = extract_numbered_procedure_items(chunks)

    assert len(result) == 1

    assert [
        item["number"]
        for item in result[0]["items"]
    ] == [1, 2]


def test_ocr_missing_space_after_number_is_supported():
    chunks = [
        {
            "section_title": "Processing",
            "page_number": 40,
            "clause_id": None,
            "content": """
1. The process shall start.
2.The request shall be reviewed.
3.The request shall be approved.
4.A result shall be communicated.
""",
        }
    ]

    result = extract_numbered_procedure_items(chunks)

    assert [
        item["number"]
        for item in result[0]["items"]
    ] == [1, 2, 3, 4]


def test_regulatory_numbers_are_not_steps():
    chunks = [
        {
            "section_title": "Security Registration",
            "page_number": 50,
            "clause_id": None,
            "content": """
1. Security shall be registered in accordance with
Proclamation No. 1147/2019 and Directive MCR/01/2020.
2. Required amendments shall be registered.
""",
        }
    ]

    result = extract_numbered_procedure_items(chunks)

    assert len(result) == 1

    assert [
        item["number"]
        for item in result[0]["items"]
    ] == [1, 2]


def test_separate_sections_remain_separate_processes():
    chunks = [
        {
            "section_title": "Application Processing",
            "page_number": 10,
            "clause_id": None,
            "content": """
1. Application shall be submitted.
2. Application shall be reviewed.
""",
        },
        {
            "section_title": "Decision Execution",
            "page_number": 20,
            "clause_id": None,
            "content": """
1. Decision shall be communicated.
2. Contract shall be prepared.
""",
        },
    ]

    result = extract_numbered_procedure_items(chunks)

    assert len(result) == 2

    assert result[0]["process_name"] == (
        "Application Processing"
    )

    assert result[1]["process_name"] == (
        "Decision Execution"
    )

    assert len(result[0]["items"]) == 2
    assert len(result[1]["items"]) == 2
    
def test_extracts_explicit_passive_role():
    action = (
        "Any credit decision shall be communicated by "
        "the Relationship Manager to the customer."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "Relationship Manager"
    ]


def test_extracts_entrusted_role():
    action = (
        "The Credit Operations Stream is entrusted with "
        "the function of undertaking analysis and appraisal."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "Credit Operations Stream"
    ]


def test_extracts_responsible_team():
    action = (
        "A designated Credit Approving Team (CAT) or "
        "individual/jointly is responsible to independently "
        "deliberate and decide on the request."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "Credit Approving Team (CAT)"
    ]


def test_extracts_reappraisal_role_without_qualification():
    action = (
        "The appeal shall be re-appraised by a credit analyst "
        "other than the one who conducted the initial appraisal."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "credit analyst"
    ]


def test_extracts_actor_and_coordination_unit():
    action = (
        "The responsible Customer Relationship Manager, "
        "in coordination with the Legal Service Team, "
        "shall prepare the contract."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "Customer Relationship Manager",
        "Legal Service Team",
    ]


def test_extracts_always_passive_role():
    action = (
        "Standard contracts shall always be designed by "
        "the legal service department."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "legal service department"
    ]


def test_extracts_explicit_can_actor():
    action = (
        "In such cases, the Customer Relationship Manager "
        "can advise the customer to apply afresh."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == [
        "Customer Relationship Manager"
    ]


def test_does_not_infer_role_from_object():
    action = (
        "Security rights backed by movable property shall "
        "be registered online through the registry."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == []


def test_does_not_infer_role_when_actor_absent():
    action = (
        "Loan disbursement shall take place only after "
        "all preconditions are fully met."
    )

    assert extract_explicit_procedure_roles(
        action
    ) == []
    
def test_procedure_mapping_execution_uses_deterministic_renderer(
    monkeypatch,
):
    """
    Procedure mapping must use deterministic rendering and
    must never call the AI provider after grounded evidence
    has been prepared.
    """

    from app.ai import grc_execution_service as service

    prepared = {
        "status": "ready",
        "capability": "procedure_mapping",
        "document": {
            "title": "Example Policy",
        },
        "document_index_id": 999,
        "evidence_count": 1,
        "evidence_chunks": [
            {
                "id": 1,
                "section_title": "Request Processing",
                "page_number": 10,
                "clause_id": None,
                "content": (
                    "4.1. Request Processing\n"
                    "1. The request shall be reviewed by "
                    "the Review Officer.\n"
                    "2. The Approval Team shall approve "
                    "the request."
                ),
            }
        ],
    }

    monkeypatch.setattr(
        service,
        "prepare_single_document_grc",
        lambda **kwargs: prepared,
    )

    def fail_if_provider_called(*args, **kwargs):
        raise AssertionError(
            "AI provider must not be called for "
            "procedure_mapping"
        )

    monkeypatch.setattr(
        service,
        "get_ai_provider",
        fail_if_provider_called,
    )

    result = service.execute_single_document_grc(
        database=None,
        capability_code="procedure_mapping",
        user_query="Map the procedures.",
        document_query="Example Policy",
    )

    assert result["status"] == "ready"
    assert result["capability"] == "procedure_mapping"
    assert result["document_index_id"] == 999
    assert result["evidence_count"] == 1

    answer = result["answer"]

    assert (
        "### Process/Procedure: Request Processing"
        in answer
    )

    assert answer.count("#### Step/Rule") == 2

    assert (
        "Responsible Role/Unit: Review Officer"
        in answer
    )

    assert (
        "Responsible Role/Unit: Approval Team"
        in answer
    )

    assert "Page: 10" in answer
