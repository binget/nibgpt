from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GRCCapability:
    code: str
    name: str
    description: str
    output_type: str
    requires_documents: bool = True
    supports_multiple_documents: bool = False


GRC_CAPABILITIES = {

    "document_summary": GRCCapability(
        code="document_summary",
        name="Document Summary",
        description=(
            "Create a grounded executive summary of "
            "an internal governance document."
        ),
        output_type="executive_summary",
    ),

    "document_classification": GRCCapability(
        code="document_classification",
        name="Document Classification",
        description=(
            "Classify a document as policy, procedure, "
            "guideline, framework, or directive."
        ),
        output_type="classification",
    ),

    "metadata_extraction": GRCCapability(
        code="metadata_extraction",
        name="Metadata Extraction",
        description=(
            "Extract structured governance and lifecycle "
            "metadata from a document."
        ),
        output_type="json",
    ),

    "expired_documents": GRCCapability(
        code="expired_documents",
        name="Expired Document Analysis",
        description=(
            "Identify expired documents and documents "
            "pending governance review."
        ),
        output_type="table",
        supports_multiple_documents=True,
    ),

    "regulatory_impact": GRCCapability(
        code="regulatory_impact",
        name="Regulatory Change Impact",
        description=(
            "Compare internal requirements with a new "
            "regulation or directive."
        ),
        output_type="table",
        supports_multiple_documents=True,
    ),

    "contradiction_analysis": GRCCapability(
        code="contradiction_analysis",
        name="Contradiction Analysis",
        description=(
            "Identify conflicting clauses, timelines, "
            "authorities, or operational mandates."
        ),
        output_type="table",
        supports_multiple_documents=True,
    ),

    "procedure_mapping": GRCCapability(
        code="procedure_mapping",
        name="Procedure Step Mapping",
        description=(
            "Extract operational workflows into "
            "ordered process steps."
        ),
        output_type="table",
    ),

    "raci_extraction": GRCCapability(
        code="raci_extraction",
        name="RACI Matrix Extraction",
        description=(
            "Map documented responsibilities to "
            "responsible, accountable, consulted, "
            "and informed roles."
        ),
        output_type="table",
    ),

    "cross_reference_mapping": GRCCapability(
        code="cross_reference_mapping",
        name="Cross-Reference Mapping",
        description=(
            "Identify internal documents, regulations, "
            "laws, standards, and forms referenced "
            "by a document."
        ),
        output_type="table",
    ),

    "gap_analysis": GRCCapability(
        code="gap_analysis",
        name="Policy Gap Analysis",
        description=(
            "Compare internal controls with an approved "
            "external compliance framework."
        ),
        output_type="table",
        supports_multiple_documents=True,
    ),

    "ambiguity_audit": GRCCapability(
        code="ambiguity_audit",
        name="Ambiguity and Measurability Audit",
        description=(
            "Identify vague or unmeasurable governance "
            "requirements."
        ),
        output_type="table",
    ),

    "audit_checklist": GRCCapability(
        code="audit_checklist",
        name="Internal Audit Checklist",
        description=(
            "Convert mandatory document requirements "
            "into an audit verification checklist."
        ),
        output_type="table",
    ),

    "document_revision": GRCCapability(
        code="document_revision",
        name="Document Revision",
        description=(
            "Generate a grounded revised document while "
            "identifying additions and removals."
        ),
        output_type="document",
        supports_multiple_documents=True,
    ),

    "document_generation": GRCCapability(
        code="document_generation",
        name="New Governance Document",
        description=(
            "Generate a new structured governance "
            "document from supplied requirements "
            "and approved standards."
        ),
        output_type="document",
        requires_documents=False,
        supports_multiple_documents=True,
    ),

    "role_specific_view": GRCCapability(
        code="role_specific_view",
        name="Role-Specific Compliance View",
        description=(
            "Extract operational obligations relevant "
            "to a specified organizational role."
        ),
        output_type="structured_answer",
    ),

    "scenario_evaluation": GRCCapability(
        code="scenario_evaluation",
        name="Operational Scenario Evaluation",
        description=(
            "Determine whether an operational action is "
            "permitted, conditionally permitted, or "
            "prohibited by internal documents."
        ),
        output_type="decision",
        supports_multiple_documents=True,
    ),

    "employee_faq": GRCCapability(
        code="employee_faq",
        name="Employee FAQ",
        description=(
            "Generate grounded operational questions "
            "and concise answers from a document."
        ),
        output_type="faq",
    ),
}


def get_grc_capability(
    code: str,
) -> Optional[GRCCapability]:

    return GRC_CAPABILITIES.get(
        (code or "").strip()
    )


def list_grc_capabilities() -> list[GRCCapability]:

    return list(
        GRC_CAPABILITIES.values()
    )
