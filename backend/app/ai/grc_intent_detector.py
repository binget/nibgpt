import re
from dataclasses import dataclass
from typing import Optional

from app.ai.grc_capability_registry import (
    GRCCapability,
    get_grc_capability,
)


@dataclass(frozen=True)
class GRCIntent:
    capability: GRCCapability
    confidence: float
    reason: str


# Strong phrases only.
#
# These describe the requested OPERATION, not document
# names, business subjects, departments, or entities.
GRC_INTENT_PATTERNS = {

    "expired_documents": (
        r"\bexpired documents?\b",
        r"\bdocuments? (?:due|pending) for review\b",
        r"\bdocuments? pending review\b",
    ),

    "contradiction_analysis": (
        r"\bcontradict(?:ion|ory|ing)?\b",
        r"\bconflicting clauses?\b",
        r"\bconflicting articles?\b",
        r"\bpolicy conflicts?\b",
    ),

    "procedure_mapping": (
        r"\bprocedure step mapping\b",
        r"\bmap (?:the )?(?:procedure|process|workflow)\b",
        r"\bstep[- ]by[- ]step (?:process|procedure|workflow)\b",
    ),

    "raci_extraction": (
        r"\braci\b",
        r"\braci matrix\b",
    ),

    "cross_reference_mapping": (
        r"\bcross[- ]references?\b",
        r"\breferenced (?:documents?|policies|regulations|laws|standards)\b",
        r"\bdependency mapping\b",
    ),

    "gap_analysis": (
        r"\bgap analysis\b",
        r"\bcompliance gaps?\b",
        r"\bcontrol gaps?\b",
    ),

    "ambiguity_audit": (
        r"\bambiguity audit\b",
        r"\bambiguous language\b",
        r"\bvague (?:language|requirements?|clauses?)\b",
        r"\bunmeasurable (?:language|requirements?|clauses?)\b",
    ),

    "audit_checklist": (
        r"\baudit checklist\b",
        r"\binternal audit checklist\b",
        r"\bverification checklist\b",
    ),

    "document_revision": (
        r"\brevise (?:this|the|a) document\b",
        r"\brevise (?:this|the|a) policy\b",
        r"\bgenerate (?:a )?revised document\b",
        r"\brevised draft\b",
    ),

    "document_generation": (
        r"\bgenerate (?:a )?new\b.*\b(?:policy|procedure|guideline|directive|framework|document)\b",
        r"\bdraft (?:a )?new\b.*\b(?:policy|procedure|guideline|directive|framework)\b",
        r"\bcreate (?:a )?new\b.*\b(?:policy|procedure|guideline|directive|framework)\b",
    ),

    "role_specific_view": (
        r"\bobligations? (?:for|of)\b",
        r"\bresponsibilities (?:for|of)\b",
        r"\brules (?:for|applicable to)\b",
        r"\brole[- ]specific\b",
    ),

    "scenario_evaluation": (
        r"\bis (?:this|it)\b.*\bpermitted\b",
        r"\bis (?:this|it)\b.*\bprohibited\b",
        r"\bis (?:this|it)\b.*\ballowed\b",
        r"\bconditionally permitted\b",
        r"\bevaluate (?:this|the)\b.*\bscenario\b",
    ),

    "employee_faq": (
        r"\bemployee faq\b",
        r"\bgenerate (?:an? )?faq\b",
        r"\bfrequently asked questions\b",
    ),

    "metadata_extraction": (
        r"\bextract (?:the )?metadata\b",
        r"\bdocument metadata\b",
        r"\bgovernance metadata\b",
    ),

    "document_classification": (
        r"\bclassify (?:this|the) document\b",
        r"\bwhat type of document\b",
        r"\bis (?:this|the) document (?:a )?(?:policy|procedure|guideline|framework|directive)\b",
    ),

    "regulatory_impact": (
        r"\bregulatory (?:change )?impact\b",
        r"\bimpact of (?:the )?(?:new )?(?:regulation|directive)\b",
        r"\bcompare .* (?:regulation|directive)\b",
    ),

    "document_summary": (
        r"\bsummarize (?:this|the) document\b",
        r"\bsummarize (?:this|the) policy\b",
        r"\bexecutive summary\b",
    ),
}


def normalize_grc_query(
    query: str,
) -> str:

    return " ".join(
        (query or "")
        .lower()
        .strip()
        .split()
    )


def detect_grc_intent(
    query: str,
) -> Optional[GRCIntent]:

    normalized = normalize_grc_query(
        query
    )

    if not normalized:
        return None

    for capability_code, patterns in (
        GRC_INTENT_PATTERNS.items()
    ):

        for pattern in patterns:

            if re.search(
                pattern,
                normalized,
                flags=re.IGNORECASE,
            ):

                capability = (
                    get_grc_capability(
                        capability_code
                    )
                )

                if capability is None:
                    continue

                return GRCIntent(
                    capability=capability,
                    confidence=0.95,
                    reason=(
                        "Matched a strong GRC "
                        "operation pattern."
                    ),
                )

    return None
