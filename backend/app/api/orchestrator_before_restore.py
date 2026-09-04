from __future__ import annotations

import inspect
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Callable

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.database.session import get_db


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/orchestrator",
    tags=["Orchestrator"],
)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class OrchestratorRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
    )

    conversation_id: int | str | None = None


class OrchestratorResponse(BaseModel):
    route: str
    confidence: int
    reason: str

    success: bool

    answer: str | None = None

    report: Any | None = None
    context: Any | None = None

    warnings: list[str] = Field(
        default_factory=list
    )

    sources: list[dict[str, Any]] = Field(
        default_factory=list
    )

    retrieved_at: str | None = None


# ============================================================
# ROUTE DECISION
# ============================================================

class RouteDecision(BaseModel):
    route: str
    confidence: int
    reason: str


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_prompt(
    prompt: str,
) -> str:

    return " ".join(
        (prompt or "")
        .strip()
        .lower()
        .split()
    )


# ============================================================
# REPORTING DETECTION
# ============================================================

def is_reporting_question(
    prompt: str,
) -> bool:

    text = normalize_prompt(
        prompt
    )

    reporting_indicators = (
        "show ",
        "report",
        "total ",
        "sum ",
        "average ",
        "avg ",
        "count ",
        "how many",
        "top ",
        "bottom ",
        "balance",
        "deposit",
        "branch",
        "district",
        "customer",
        "account",
        "active accounts",
        "inactive accounts",
        "transaction",
        "transactions",
        "by branch",
        "by district",
        "by customer",
        "group by",
        "highest",
        "lowest",
    )

    return any(
        indicator in text
        for indicator in reporting_indicators
    )


# ============================================================
# INTERNAL DOCUMENT / KNOWLEDGE DETECTION
# ============================================================

def is_internal_knowledge_question(
    prompt: str,
) -> bool:

    text = normalize_prompt(
        prompt
    )

    # Reporting must win over knowledge.
    if is_reporting_question(
        prompt
    ):
        return False

    indicators = (
        "policy",
        "procedure",
        "guideline",
        "manual",
        "framework",
        "directive",
        "responsibility",
        "responsibilities",
        "who is responsible",
        "who approves",
        "who shall",
        "requirement",
        "requirements",
        "legislative requirement",
        "internal document",
        "document",
        "summarize the",
        "according to the",
        "what does the policy",
        "what are the duties",
        "what is the purpose",
        "authority",
        "authorities",
        "compliance requirement",
    )

    return any(
        indicator in text
        for indicator in indicators
    )


# ============================================================
# COMPETITOR DETECTION
# ============================================================

def is_competitor_question(
    prompt: str,
) -> bool:

    text = normalize_prompt(
        prompt
    )

    indicators = (
        "competitor",
        "compare nib",
        "nib vs",
        "versus nib",
        "cbe",
        "commercial bank of ethiopia",
        "dashen",
        "awash bank",
        "bank of abyssinia",
        "abyssinia bank",
        "coop bank",
        "cooperative bank of oromia",
        "wegagen",
        "zemen bank",
        "hibret bank",
        "oromia bank",
    )

    return any(
        indicator in text
        for indicator in indicators
    )


# ============================================================
# NIB PUBLIC WEBSITE DETECTION
# ============================================================

def is_nib_website_question(
    prompt: str,
) -> bool:

    text = normalize_prompt(
        prompt
    )

    indicators = (
        "nib website",
        "nib bank website",
        "nib international bank",
        "nib mobile banking",
        "nib internet banking",
        "nib digital banking",
        "nib loan",
        "nib loans",
        "nib product",
        "nib products",
        "nib service",
        "nib services",
        "nib management",
        "nib executive",
        "nib ceo",
        "board of directors",
        "executive management",
        "district director",
    )

    return any(
        indicator in text
        for indicator in indicators
    )


# ============================================================
# ROUTE CLASSIFIER
# ============================================================

def classify_prompt(
    prompt: str,
) -> RouteDecision:

    if is_competitor_question(
        prompt
    ):
        return RouteDecision(
            route="competitor",
            confidence=95,
            reason=(
                "The prompt requests competitor "
                "or comparative banking intelligence."
            ),
        )

    if is_nib_website_question(
        prompt
    ):
        return RouteDecision(
            route="web",
            confidence=93,
            reason=(
                "The prompt requests public "
                "information about NIB."
            ),
        )

    if is_internal_knowledge_question(
        prompt
    ):
        return RouteDecision(
            route="knowledge",
            confidence=90,
            reason=(
                "The prompt appears to request "
                "internal institutional knowledge."
            ),
        )

    if is_reporting_question(
        prompt
    ):
        return RouteDecision(
            route="reporting",
            confidence=92,
            reason=(
                "The prompt appears to request "
                "structured banking data or a report."
            ),
        )

    return RouteDecision(
        route="general",
        confidence=75,
        reason=(
            "The prompt does not clearly match "
            "reporting, internal knowledge, "
            "website, or competitor intelligence."
        ),
    )


# ============================================================
# SAFE LAZY IMPORT
# ============================================================

def load_callable(
    candidates: list[
        tuple[str, str]
    ],
) -> Callable | None:

    """
    Try possible module/function combinations.

    Important:
    Optional AI modules are NOT imported when
    FastAPI starts. This prevents one stale module
    from taking down authentication and the whole API.
    """

    for (
        module_name,
        function_name,
    ) in candidates:

        try:

            module = import_module(
                module_name
            )

            function = getattr(
                module,
                function_name,
                None,
            )

            if callable(
                function
            ):
                return function

        except (
            ImportError,
            ModuleNotFoundError,
            AttributeError,
        ):
            continue

    return None


# ============================================================
# FLEXIBLE FUNCTION CALL
# ============================================================

def call_supported_arguments(
    function: Callable,
    **kwargs,
):

    """
    Calls a project function using only arguments
    supported by that function.

    This makes the orchestrator compatible with
    existing NIBGPT services whose signatures may
    differ slightly.
    """

    signature = inspect.signature(
        function
    )

    parameters = (
        signature.parameters
    )

    # Function accepts **kwargs
    if any(
        parameter.kind
        == inspect.Parameter.VAR_KEYWORD
        for parameter
        in parameters.values()
    ):
        return function(
            **kwargs
        )

    supported = {}

    for key, value in kwargs.items():

        if key in parameters:
            supported[key] = value

    return function(
        **supported
    )


# ============================================================
# STANDARDIZE SERVICE RESULT
# ============================================================

def normalize_result(
    result: Any,
) -> dict[str, Any]:

    if result is None:

        return {
            "success": False,
            "answer": None,
            "warnings": [
                "The service returned no result."
            ],
            "sources": [],
            "retrieved_at": None,
        }

    if isinstance(
        result,
        str,
    ):

        return {
            "success": True,
            "answer": result,
            "warnings": [],
            "sources": [],
            "retrieved_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

    if isinstance(
        result,
        BaseModel,
    ):

        if hasattr(
            result,
            "model_dump",
        ):
            result = (
                result.model_dump()
            )
        else:
            result = result.dict()

    if isinstance(
        result,
        dict,
    ):

        return {
            "success":
                result.get(
                    "success",
                    True,
                ),

            "answer":
                result.get(
                    "answer"
                ),

            "report":
                result.get(
                    "report"
                ),

            "context":
                result.get(
                    "context"
                ),

            "warnings":
                result.get(
                    "warnings",
                    [],
                )
                or [],

            "sources":
                result.get(
                    "sources",
                    [],
                )
                or [],

            "retrieved_at":
                result.get(
                    "retrieved_at"
                ),
        }

    return {
        "success": True,
        "answer": str(
            result
        ),
        "warnings": [],
        "sources": [],
        "retrieved_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# ============================================================
# KNOWLEDGE / DMS
# ============================================================

def handle_knowledge(
    database: Session,
    prompt: str,
) -> dict[str, Any]:

    function = load_callable(
        [
            (
                "app.ai.document_intelligence",
                "answer_document_question",
            ),
        ]
    )

    if not function:

        return {
            "success": False,
            "answer": (
                "Document Intelligence is "
                "currently unavailable."
            ),
            "warnings": [
                (
                    "Could not load "
                    "answer_document_question."
                )
            ],
            "sources": [],
        }

    result = call_supported_arguments(
        function,
        database=database,
        db=database,
        question=prompt,
        prompt=prompt,
    )

    return normalize_result(
        result
    )


# ============================================================
# NIB WEBSITE
# ============================================================

def handle_web(
    prompt: str,
) -> dict[str, Any]:

    function = load_callable(
        [
            (
                "app.ai.website_intelligence",
                "answer_nib_website_question",
            ),
            (
                "app.ai.nib_website",
                "answer_nib_website_question",
            ),
            (
                "app.ai.web_intelligence",
                "answer_nib_website_question",
            ),
            (
                "app.api.web_intelligence",
                "answer_nib_website_question",
            ),
        ]
    )

    if not function:

        return {
            "success": False,
            "answer": (
                "NIB public website intelligence "
                "is currently unavailable."
            ),
            "warnings": [
                (
                    "Could not locate "
                    "answer_nib_website_question."
                )
            ],
            "sources": [],
        }

    result = call_supported_arguments(
        function,
        question=prompt,
        prompt=prompt,
    )

    return normalize_result(
        result
    )


# ============================================================
# COMPETITOR INTELLIGENCE
# ============================================================

def handle_competitor(
    prompt: str,
) -> dict[str, Any]:

    function = load_callable(
        [
            (
                "app.ai.competitor_intelligence",
                "answer_competitor_question",
            ),
            (
                "app.ai.competitor",
                "answer_competitor_question",
            ),
            (
                "app.api.intelligence",
                "answer_competitor_question",
            ),
        ]
    )

    if not function:

        return {
            "success": False,
            "answer": (
                "Competitor intelligence is "
                "currently unavailable."
            ),
            "warnings": [
                (
                    "Could not locate "
                    "answer_competitor_question."
                )
            ],
            "sources": [],
        }

    result = call_supported_arguments(
        function,
        question=prompt,
        prompt=prompt,
    )

    return normalize_result(
        result
    )


# ============================================================
# REPORTING
# ============================================================

def handle_reporting(
    database: Session,
    prompt: str,
    conversation_id: int | str | None,
) -> dict[str, Any]:

    """
    Reporting code evolved during NIBGPT development.

    We resolve it lazily so an unrelated reporting
    import error cannot break login/authentication.
    """

    function = load_callable(
        [
            (
                "app.ai.reporting",
                "answer_reporting_question",
            ),
            (
                "app.ai.reporting",
                "generate_report",
            ),
            (
                "app.api.reasoning",
                "answer_reporting_question",
            ),
            (
                "app.api.query_plan",
                "answer_reporting_question",
            ),
            (
                "app.api.prompt_pipeline",
                "process_reporting_prompt",
            ),
        ]
    )

    if not function:

        return {
            "success": False,
            "answer": (
                "The reporting engine is currently "
                "unavailable because its reporting "
                "entry function could not be located."
            ),
            "report": None,
            "context": None,
            "warnings": [
                (
                    "Reporting function was not "
                    "found by the orchestrator."
                )
            ],
            "sources": [],
        }

    result = call_supported_arguments(
        function,
        database=database,
        db=database,
        question=prompt,
        prompt=prompt,
        conversation_id=conversation_id,
    )

    return normalize_result(
        result
    )


# ============================================================
# GENERAL AI
# ============================================================

def handle_general(
    prompt: str,
) -> dict[str, Any]:

    try:

        from app.ai.providers.factory import (
            get_ai_provider,
        )

        provider = (
            get_ai_provider()
        )

        system_prompt = (
            "You are NIBGPT, the internal AI "
            "assistant for NIB International Bank. "
            "Be accurate, concise and professional. "
            "Do not invent internal bank facts, "
            "policies, procedures or figures. "
            "Questions requiring bank data should "
            "be handled by the reporting engine, "
            "and internal-document questions should "
            "be handled by Document Intelligence."
        )

        answer = provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        return {
            "success": True,
            "answer":
                (
                    answer
                    or ""
                ).strip(),
            "warnings": [],
            "sources": [],
            "retrieved_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

    except Exception as error:

        return {
            "success": False,
            "answer": (
                "The general AI service is "
                "currently unavailable."
            ),
            "warnings": [
                str(error)
            ],
            "sources": [],
        }


# ============================================================
# MAIN ASK ENDPOINT
# ============================================================

@router.post(
    "/ask",
    response_model=OrchestratorResponse,
)
def ask_orchestrator(
    payload: OrchestratorRequest,
    database: Session = Depends(
        get_db
    ),
):

    prompt = (
        payload.prompt
        or ""
    ).strip()

    if not prompt:

        raise HTTPException(
            status_code=400,
            detail="Prompt is required.",
        )

    decision = classify_prompt(
        prompt
    )

    try:

        if decision.route == "knowledge":

            result = handle_knowledge(
                database=database,
                prompt=prompt,
            )

        elif decision.route == "web":

            result = handle_web(
                prompt=prompt,
            )

        elif decision.route == "competitor":

            result = handle_competitor(
                prompt=prompt,
            )

        elif decision.route == "reporting":

            result = handle_reporting(
                database=database,
                prompt=prompt,
                conversation_id=(
                    payload.conversation_id
                ),
            )

        else:

            result = handle_general(
                prompt=prompt,
            )

    except Exception as error:

        return OrchestratorResponse(
            route=decision.route,
            confidence=decision.confidence,
            reason=decision.reason,
            success=False,
            answer=(
                "NIBGPT could not complete "
                "the request."
            ),
            report=None,
            context=None,
            warnings=[
                str(error)
            ],
            sources=[],
            retrieved_at=None,
        )

    return OrchestratorResponse(
        route=decision.route,

        confidence=(
            decision.confidence
        ),

        reason=(
            decision.reason
        ),

        success=result.get(
            "success",
            False,
        ),

        answer=result.get(
            "answer"
        ),

        report=result.get(
            "report"
        ),

        context=result.get(
            "context"
        ),

        warnings=result.get(
            "warnings",
            [],
        ),

        sources=result.get(
            "sources",
            [],
        ),

        retrieved_at=result.get(
            "retrieved_at"
        ),
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get(
    "/health"
)
def orchestrator_health():

    return {
        "service": "NIBGPT Orchestrator",
        "status": "ok",
        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }