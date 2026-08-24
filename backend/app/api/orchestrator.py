from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.ai.orchestrator import (
    build_prompt_from_context,
    classify_prompt,
    merge_reporting_context,
)

from app.ai.query_executor import (
    execute_governed_prompt,
)

from app.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    ReportingContext,
)





router = APIRouter(
    prefix="/api/orchestrator",
    tags=["NIBGPT Orchestrator"],
)


@router.post(
    "/ask",
    response_model=OrchestratorResponse,
)
def ask_nibgpt(
    payload: OrchestratorRequest,
    database: Session = Depends(
        get_db
    ),
):
    # --------------------------------------------------
    # Build / merge structured reporting context
    # --------------------------------------------------

    previous_context = None

    if payload.context:
        previous_context = (
            payload.context.model_dump()
        )

    merged_context = (
        merge_reporting_context(
            previous_context=(
                previous_context
            ),
            prompt=payload.prompt,
        )
    )

    # --------------------------------------------------
    # Build effective prompt
    #
    # First question:
    # use the original natural-language prompt.
    #
    # Follow-up:
    # rebuild the reporting request from
    # structured conversational context.
    # --------------------------------------------------

    if previous_context:
        effective_prompt = (
            build_prompt_from_context(
                merged_context
            )
        )
    else:
        effective_prompt = (
            payload.prompt
        )

    # --------------------------------------------------
    # Route request
    # --------------------------------------------------

    decision = classify_prompt(
        effective_prompt
    )

    # --------------------------------------------------
    # Reporting Agent
    # --------------------------------------------------

    if decision.route == "reporting":
        report = (
            execute_governed_prompt(
                database=database,
                prompt=effective_prompt,
                domain_id=None,
                requested_limit=(
                    payload.requested_limit
                ),
                maximum_entities=(
                    payload.maximum_entities
                ),
                maximum_path_depth=(
                    payload.maximum_path_depth
                ),
                user_role=(
                    payload.user_role
                ),
            )
        )
        
        report_answer = (
            report.get(
                "answer"
            )
        )

        return OrchestratorResponse(
            route="reporting",
            confidence=(
                decision.confidence
            ),
            reason=decision.reason,
            success=report.get(
                "success",
                False,
            ),
            answer=(
                report_answer
            ),
            report=report,
            warnings=report.get(
                "warnings",
                [],
            ),
            context=ReportingContext(
                **merged_context
            ),
        )

    # --------------------------------------------------
    # Knowledge Agent
    # --------------------------------------------------

    if decision.route == "knowledge":
        return OrchestratorResponse(
            route="knowledge",
            confidence=(
                decision.confidence
            ),
            reason=decision.reason,
            success=True,
            answer=(
                "The Knowledge Agent is not "
                "connected yet. This request "
                "was correctly identified as "
                "a knowledge question."
            ),
            context=None,
        )

    # --------------------------------------------------
    # General AI Assistant
    # --------------------------------------------------

    if decision.route == "general":
        return OrchestratorResponse(
            route="general",
            confidence=(
                decision.confidence
            ),
            reason=decision.reason,
            success=True,
            answer=None,
            report=None,
            warnings=[],
            context=None,
    )

    return OrchestratorResponse(
        route=(decision.route if hasattr(decision, "route") else "general"),
        confidence=(
            decision.confidence if hasattr(decision, "confidence") else 0.0
        ),
        reason=(
            decision.reason if hasattr(decision, "reason") else "Unknown route"
        ),
        success=False,
        answer=(
            "The request could not be processed "
            "with the selected route."
        ),
        context=None,
    )