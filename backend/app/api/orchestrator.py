from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy import (
    select,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.ai.orchestrator import (
    build_prompt_from_context,
    classify_prompt,
    is_follow_up_prompt,
    merge_reporting_context,
)

from app.ai.query_executor import (
    execute_governed_prompt,
)

from app.ai.web_intelligence import (
    answer_nib_website_question,
)

from app.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    ReportingContext,
)

from app.models.conversation import (
    ChatMessage,
    Conversation,
)

from app.ai.competitor_intelligence import (
    answer_competitor_question,
    is_competitor_question,
)


router = APIRouter(
    prefix="/api/orchestrator",
    tags=["NIBGPT Orchestrator"],
)


# ============================================================
# Public NIB web-intelligence routing
#
# These phrases should never be rewritten through old reporting
# context. This specifically protects questions such as:
#
#   Who are the district directors?
#   Who are the department directors?
#   Who are the deputy chief executives?
#
# from being misrouted to governed reporting merely because
# words such as "district" occur in the question.
# ============================================================

NIB_PUBLIC_LEADERSHIP_TERMS = {
    "ceo",
    "chief executive",
    "chief executive officer",
    "chief executive officers",
    "deputy chief",
    "deputy chief executive",
    "deputy chief executives",
    "deputy chief executive officer",
    "deputy chief executive officers",
    "deputy ceo",
    "deputy ceos",
    "deputies",
    "executive management",
    "executive managers",
    "senior management",
    "senior manager",
    "senior managers",
    "district director",
    "district directors",
    "department director",
    "department directors",
}


def looks_like_nib_public_leadership_question(
    prompt: str,
) -> bool:
    normalized = (
        " ".join(
            prompt.lower().split()
        )
    )

    return any(
        term in normalized
        for term in NIB_PUBLIC_LEADERSHIP_TERMS
    )


# ============================================================
# Reporting-context recovery
# ============================================================

def rebuild_reporting_context(
    database: Session,
    conversation_id: int | None,
    current_prompt: str,
) -> dict | None:
    if conversation_id is None:
        return None

    statement = (
        select(
            ChatMessage
        )
        .where(
            ChatMessage.conversation_id
            == conversation_id
        )
        .where(
            ChatMessage.role == "user"
        )
        .order_by(
            ChatMessage.created_at.asc()
        )
    )

    messages = list(
        database.scalars(
            statement
        ).all()
    )

    if not messages:
        return None

    prompts = [
        message.content.strip()
        for message in messages
        if message.content
        and message.content.strip()
    ]

    # The frontend stores the current user message before
    # calling /ask. Do not treat it as previous context.
    if (
        prompts
        and prompts[-1].lower()
        == current_prompt.strip().lower()
    ):
        prompts.pop()

    if not prompts:
        return None

    context = None

    for historical_prompt in prompts:
        context = merge_reporting_context(
            previous_context=context,
            prompt=historical_prompt,
        )

    return context


def get_saved_reporting_context(
    database: Session,
    conversation_id: int | None,
) -> dict | None:
    if conversation_id is None:
        return None

    conversation = database.get(
        Conversation,
        conversation_id,
    )

    if (
        conversation is None
        or not conversation.reporting_context
    ):
        return None

    return dict(
        conversation.reporting_context
    )


# ============================================================
# Web response helper
# ============================================================

def build_web_response(
    payload: OrchestratorRequest,
    decision,
) -> OrchestratorResponse:
    try:
        web_result = (
            answer_nib_website_question(
                payload.prompt
            )
        )

        return OrchestratorResponse(
            route="web",
            confidence=(
                decision.confidence
            ),
            reason=decision.reason,
            success=web_result.get(
                "success",
                False,
            ),
            answer=web_result.get(
                "answer"
            ),
            report=None,
            context=None,
            warnings=web_result.get(
                "warnings",
                [],
            ),
            sources=web_result.get(
                "sources",
                [],
            ),
            retrieved_at=web_result.get(
                "retrieved_at"
            ),
        )

    except Exception as error:
        return OrchestratorResponse(
            route="web",
            confidence=(
                getattr(
                    decision,
                    "confidence",
                    90,
                )
            ),
            reason=(
                getattr(
                    decision,
                    "reason",
                    (
                        "The prompt appears to request "
                        "public information about "
                        "NIB International Bank."
                    ),
                )
            ),
            success=False,
            answer=(
                "NIBGPT could not retrieve "
                "the requested public NIB "
                "website information."
            ),
            report=None,
            context=None,
            warnings=[
                str(error)
            ],
            sources=[],
            retrieved_at=None,
        )


# ============================================================
# Main orchestrator endpoint
# ============================================================

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
    # --------------------------------------------------------
    # 1. Protect explicit public-leadership questions.
    #
    # "district directors" contains the word "district", but
    # it is NOT a governed-data request. Route it to the web
    # agent before any reporting-context reconstruction.
    # --------------------------------------------------------

    if (
        looks_like_nib_public_leadership_question(
            payload.prompt
        )
    ):
        raw_decision = classify_prompt(
            (
                "NIB International Bank public "
                "website leadership information"
            )
        )

        # The classifier may still call the synthetic phrase
        # general, so provide a small compatible decision
        # object without importing internal dataclasses.
        if raw_decision.route != "web":
            class WebDecision:
                route = "web"
                confidence = 95
                reason = (
                    "The prompt appears to request "
                    "public leadership information "
                    "about NIB International Bank."
                )

            raw_decision = WebDecision()

        return build_web_response(
            payload=payload,
            decision=raw_decision,
        )
        
        # --------------------------------------------------------
    # Competitor Public Intelligence
    # --------------------------------------------------------

    if is_competitor_question(
        payload.prompt
    ):
        try:
            competitor_result = (
                answer_competitor_question(
                    payload.prompt
                )
            )

            return OrchestratorResponse(
                route="competitor",
                confidence=95,
                reason=(
                    "The prompt appears to request "
                    "public competitor information."
                ),
                success=competitor_result.get(
                    "success",
                    False,
                ),
                answer=competitor_result.get(
                    "answer"
                ),
                report=None,
                context=None,
                warnings=competitor_result.get(
                    "warnings",
                    [],
                ),
                sources=competitor_result.get(
                    "sources",
                    [],
                ),
                retrieved_at=competitor_result.get(
                    "retrieved_at"
                ),
            )

        except Exception as error:
            return OrchestratorResponse(
                route="competitor",
                confidence=95,
                reason=(
                    "The prompt appears to request "
                    "public competitor information."
                ),
                success=False,
                answer=(
                    "NIBGPT could not retrieve "
                    "the requested competitor "
                    "information."
                ),
                report=None,
                context=None,
                warnings=[
                    str(error)
                ],
                sources=[],
                retrieved_at=None,
            )

    # --------------------------------------------------------
    # 2. Classify the CURRENT prompt before allowing an old
    # reporting context to rewrite it.
    # --------------------------------------------------------

    current_decision = classify_prompt(
        payload.prompt
    )

    # Explicit web request.
    if current_decision.route == "web":
        return build_web_response(
            payload=payload,
            decision=current_decision,
        )

    # Explicit institutional-knowledge request.
    if current_decision.route == "knowledge":
        return OrchestratorResponse(
            route="knowledge",
            confidence=(
                current_decision.confidence
            ),
            reason=current_decision.reason,
            success=True,
            answer=(
                "The Knowledge Agent is not connected yet. "
                "This request was correctly identified as "
                "a knowledge question."
            ),
            report=None,
            context=None,
            warnings=[],
            sources=[],
            retrieved_at=None,
        )

    # --------------------------------------------------------
    # 3. Determine whether this is a reporting request or a
    # reporting follow-up.
    # --------------------------------------------------------

    saved_context = (
        payload.context.model_dump()
        if payload.context
        else None
    )

    if saved_context is None:
        saved_context = (
            get_saved_reporting_context(
                database=database,
                conversation_id=(
                    payload.conversation_id
                ),
            )
        )

    is_reporting_follow_up = (
        saved_context is not None
        and is_follow_up_prompt(
            payload.prompt
        )
    )

    is_reporting_request = (
        current_decision.route
        == "reporting"
        or is_reporting_follow_up
    )

    # A normal general question must never be rewritten from
    # old reporting context.
    if not is_reporting_request:
        return OrchestratorResponse(
            route="general",
            confidence=(
                current_decision.confidence
            ),
            reason=current_decision.reason,
            success=True,
            answer=None,
            report=None,
            context=None,
            warnings=[],
            sources=[],
            retrieved_at=None,
        )

    # --------------------------------------------------------
    # 4. Resolve reporting context only for reporting.
    # --------------------------------------------------------

    previous_context = (
        saved_context
    )

    if (
        previous_context is None
        and payload.conversation_id
        is not None
    ):
        previous_context = (
            rebuild_reporting_context(
                database=database,
                conversation_id=(
                    payload.conversation_id
                ),
                current_prompt=(
                    payload.prompt
                ),
            )
        )

    merged_context = (
        merge_reporting_context(
            previous_context=(
                previous_context
            ),
            prompt=payload.prompt,
        )
    )

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

    # Reclassify the fully rebuilt reporting prompt.
    decision = classify_prompt(
        effective_prompt
    )

    # --------------------------------------------------------
    # 5. Governed Reporting Agent
    # --------------------------------------------------------

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

        if (
            report.get(
                "success",
                False,
            )
            and payload.conversation_id
            is not None
        ):
            conversation = (
                database.get(
                    Conversation,
                    payload.conversation_id,
                )
            )

            if conversation is not None:
                conversation.reporting_context = (
                    merged_context
                )

                conversation.updated_at = (
                    datetime.utcnow()
                )

                database.commit()

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
            answer=report.get(
                "answer"
            ),
            report=report,
            context=ReportingContext(
                **merged_context
            ),
            warnings=report.get(
                "warnings",
                [],
            ),
            sources=[],
            retrieved_at=None,
        )

    # This should be rare, but do not execute another route
    # implicitly after reporting-context reconstruction.
    return OrchestratorResponse(
        route=(
            getattr(
                decision,
                "route",
                "general",
            )
        ),
        confidence=(
            getattr(
                decision,
                "confidence",
                0,
            )
        ),
        reason=(
            getattr(
                decision,
                "reason",
                "Unknown route",
            )
        ),
        success=False,
        answer=(
            "The request could not be processed "
            "with the selected route."
        ),
        report=None,
        context=None,
        warnings=[],
        sources=[],
        retrieved_at=None,
    )