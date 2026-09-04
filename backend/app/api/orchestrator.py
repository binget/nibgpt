from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy import (
    select,
)

from sqlalchemy.orm import (
    Session,
)

# ============================================================
# DATABASE
# ============================================================

from app.database.session import (
    get_db,
)

# ============================================================
# REQUEST / RESPONSE SCHEMAS
# ============================================================

from app.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    ReportingContext,
)

# ============================================================
# REAL NIBGPT ORCHESTRATION ENGINE
# ============================================================

from app.ai.orchestrator import (
    classify_prompt,
    extract_reporting_context,
    merge_reporting_context,
    build_prompt_from_context,
    is_follow_up_prompt,
)

# ============================================================
# REAL REPORTING ENGINE
# ============================================================

from app.ai.query_executor import (
    execute_governed_prompt,
)

# ============================================================
# REAL GENERAL AI
# ============================================================

from app.ai.general_agent import (
    answer_general_question,
)

# ============================================================
# DOCUMENT INTELLIGENCE
# ============================================================

from app.ai.document_intelligence import (
    answer_document_question,
)

# ============================================================
# NIB PUBLIC WEBSITE INTELLIGENCE
# ============================================================

from app.ai.web_intelligence import (
    answer_nib_website_question,
)

# ============================================================
# COMPETITOR INTELLIGENCE
# ============================================================

from app.ai.competitor_intelligence import (
    answer_competitor_question,
    detect_competitors,
)

# ============================================================
# CONVERSATION MODELS
# ============================================================

from app.models.conversation import (
    ChatMessage,
    Conversation,
)


router = APIRouter(
    prefix="/api/orchestrator",
    tags=["NIBGPT Orchestrator"],
)


# ============================================================
# CONVERSATION HISTORY
# ============================================================

def load_conversation_history(
    database: Session,
    conversation_id: int | None,
    current_prompt: str,
) -> list[dict[str, str]]:

    if conversation_id is None:
        return []

    conversation = database.get(
        Conversation,
        conversation_id,
    )

    if conversation is None:
        return []

    statement = (
        select(
            ChatMessage
        )
        .where(
            ChatMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ChatMessage.created_at.desc()
        )
        .limit(8)
    )

    messages = list(
        database.scalars(
            statement
        ).all()
    )

    # Query is newest first.
    messages.reverse()

    history: list[
        dict[str, str]
    ] = []

    for message in messages:

        role = (
            message.role
            .strip()
            .lower()
        )

        if role not in {
            "user",
            "assistant",
        }:
            continue

        content = (
            message.content
            or ""
        ).strip()

        if not content:
            continue

        history.append(
            {
                "role": role,
                "content": content,
            }
        )

    # Frontend may already have saved the
    # current user prompt before calling /ask.
    #
    # Remove duplicate current prompt.

    if history:

        last_message = history[-1]

        if (
            last_message["role"]
            == "user"
            and
            last_message["content"].strip()
            == current_prompt.strip()
        ):
            history.pop()

    return history


# ============================================================
# REPORTING CONTEXT
# ============================================================

def prepare_reporting_prompt(
    payload: OrchestratorRequest,
) -> tuple[
    str,
    ReportingContext,
]:

    prompt = (
        payload.prompt
        or ""
    ).strip()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Only inherit old reporting context when the new prompt
    # is actually a follow-up.
    #
    # This prevents:
    #
    #   Show top 10 customers by deposit balance
    #
    # followed by:
    #
    #   Show active account report by branch
    #
    # from accidentally inheriting "top 10 customers".
    # --------------------------------------------------------

    follow_up = is_follow_up_prompt(
        prompt
    )

    previous_context = None

    if (
        follow_up
        and payload.context is not None
    ):

        if hasattr(
            payload.context,
            "model_dump",
        ):
            previous_context = (
                payload.context.model_dump()
            )
        else:
            previous_context = (
                payload.context.dict()
            )

    # --------------------------------------------------------
    # Follow-up
    # --------------------------------------------------------

    if (
        follow_up
        and previous_context
    ):

        merged_context = (
            merge_reporting_context(
                previous_context=(
                    previous_context
                ),
                prompt=prompt,
            )
        )

        reporting_prompt = (
            build_prompt_from_context(
                merged_context
            )
        )

        context = ReportingContext(
            **merged_context
        )

        return (
            reporting_prompt,
            context,
        )

    # --------------------------------------------------------
    # Standalone reporting request
    #
    # DO NOT inherit previous reporting context.
    # --------------------------------------------------------

    current_context = (
        extract_reporting_context(
            prompt
        )
    )

    context = ReportingContext(
        **current_context
    )

    return (
        prompt,
        context,
    )


# ============================================================
# NORMALIZE REPORTING RESULT
# ============================================================

def normalize_reporting_result(
    result,
    context: ReportingContext,
) -> dict:

    if not isinstance(
        result,
        dict,
    ):
        return {
            "success": False,
            "answer": (
                "The reporting engine returned "
                "an invalid response."
            ),
            "report": None,
            "context": context,
            "warnings": [],
            "sources": [],
        }

    success = result.get(
        "success",
        False,
    )

    answer = result.get(
        "answer"
    )

    report = result.get(
        "report"
    )

    # Some versions of the query executor return
    # the report fields directly instead of nesting
    # them under "report".
    #
    # Preserve the complete result so the frontend
    # does not lose SQL/report/table metadata.

    if (
        success
        and report is None
    ):
        report = result

    warnings = (
        result.get(
            "warnings"
        )
        or []
    )

    return {
        "success": success,
        "answer": answer,
        "report": report,
        "context": context,
        "warnings": warnings,
        "sources": (
            result.get(
                "sources"
            )
            or []
        ),
    }


# ============================================================
# REPORTING
# ============================================================

def handle_reporting(
    database: Session,
    payload: OrchestratorRequest,
) -> dict:

    (
        reporting_prompt,
        reporting_context,
    ) = prepare_reporting_prompt(
        payload
    )

    result = execute_governed_prompt(
        database=database,
        prompt=reporting_prompt,
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

    return normalize_reporting_result(
        result=result,
        context=reporting_context,
    )


# ============================================================
# DOCUMENT INTELLIGENCE
# ============================================================

def handle_knowledge(
    database: Session,
    prompt: str,
) -> dict:

    result = answer_document_question(
        database=database,
        question=prompt,
    )

    if not isinstance(
        result,
        dict,
    ):
        return {
            "success": False,
            "answer": (
                "Document Intelligence returned "
                "an invalid response."
            ),
            "report": None,
            "context": None,
            "warnings": [],
            "sources": [],
        }

    # --------------------------------------------------------
    # Support both the older:
    #
    # source + pages
    #
    # and newer:
    #
    # sources[]
    #
    # Document Intelligence result formats.
    # --------------------------------------------------------

    sources = (
        result.get(
            "sources"
        )
        or []
    )

    if (
        not sources
        and result.get(
            "source"
        )
    ):

        source = result.get(
            "source"
        )

        if isinstance(
            source,
            dict,
        ):
            source_item = dict(
                source
            )

        else:
            source_item = {
                "title": str(
                    source
                )
            }

        if result.get(
            "pages"
        ):
            source_item[
                "pages"
            ] = result.get(
                "pages"
            )

        sources = [
            source_item
        ]

    return {
        "success": result.get(
            "success",
            False,
        ),
        "answer": result.get(
            "answer"
        ),
        "report": None,
        "context": None,
        "warnings": (
            result.get(
                "warnings"
            )
            or []
        ),
        "sources": sources,
        "retrieved_at": result.get(
            "retrieved_at"
        ),
    }


# ============================================================
# NIB PUBLIC WEBSITE
# ============================================================

def handle_web(
    prompt: str,
) -> dict:

    result = (
        answer_nib_website_question(
            question=prompt
        )
    )

    return {
        "success": result.get(
            "success",
            False,
        ),
        "answer": result.get(
            "answer"
        ),
        "report": None,
        "context": None,
        "warnings": (
            result.get(
                "warnings"
            )
            or []
        ),
        "sources": (
            result.get(
                "sources"
            )
            or []
        ),
        "retrieved_at": result.get(
            "retrieved_at"
        ),
    }


# ============================================================
# COMPETITOR INTELLIGENCE
# ============================================================

def handle_competitor(
    prompt: str,
) -> dict:

    result = (
        answer_competitor_question(
            question=prompt
        )
    )

    return {
        "success": result.get(
            "success",
            False,
        ),
        "answer": result.get(
            "answer"
        ),
        "report": None,
        "context": None,
        "warnings": (
            result.get(
                "warnings"
            )
            or []
        ),
        "sources": (
            result.get(
                "sources"
            )
            or []
        ),
        "retrieved_at": result.get(
            "retrieved_at"
        ),
    }


# ============================================================
# GENERAL AI
# ============================================================

def handle_general(
    database: Session,
    payload: OrchestratorRequest,
) -> dict:

    normalized = (
        " ".join(
            (payload.prompt or "")
            .lower()
            .strip()
            .split()
        )
    )

    normalized_no_question = (
        normalized.rstrip("?")
    )

    # --------------------------------------------------------
    # Instant deterministic answers
    # --------------------------------------------------------

    if normalized_no_question in {
        "who are you",
        "what are you",
        "what is nibgpt",
        "introduce yourself",
        "tell me about yourself",
    }:

        return {
            "success": True,
            "answer": (
                "I am NIBGPT, NIB International Bank's AI assistant. "
                "I can help with reporting, internal knowledge, "
                "NIB public information, competitor intelligence, "
                "and general questions."
            ),
            "report": None,
            "context": None,
            "warnings": [],
            "sources": [],
        }

    if normalized_no_question in {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    }:

        return {
            "success": True,
            "answer": (
                "Hello! I am NIBGPT. How can I help you?"
            ),
            "report": None,
            "context": None,
            "warnings": [],
            "sources": [],
        }

    # --------------------------------------------------------
    # Normal AI conversation
    # --------------------------------------------------------

    history = (
        load_conversation_history(
            database=database,
            conversation_id=(
                payload.conversation_id
            ),
            current_prompt=(
                payload.prompt
            ),
        )
    )

    answer = (
        answer_general_question(
            prompt=payload.prompt,
            history=history,
        )
    )

    return {
        "success": True,
        "answer": answer,
        "report": None,
        "context": None,
        "warnings": [],
        "sources": [],
    }


# ============================================================
# COMPETITOR ROUTING
# ============================================================

def is_competitor_request(
    prompt: str,
) -> bool:

    try:

        competitors = (
            detect_competitors(
                prompt
            )
        )

        return bool(
            competitors
        )

    except Exception:
        return False


# ============================================================
# MAIN NIBGPT ENDPOINT
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

    prompt = (
        payload.prompt
        or ""
    ).strip()

    if not prompt:

        raise HTTPException(
            status_code=400,
            detail="Prompt is required.",
        )

    # ========================================================
    # COMPETITOR
    #
    # Competitor detection happens before the normal
    # classifier because competitor intelligence is a
    # separate approved-source system.
    # ========================================================

    if is_competitor_request(
        prompt
    ):

        route = "competitor"
        confidence = 95

        reason = (
            "The prompt appears to request "
            "approved competitor intelligence."
        )

    else:

        decision = classify_prompt(
            prompt
        )

        route = decision.route
        confidence = (
            decision.confidence
        )
        reason = (
            decision.reason
        )

    try:

        # ====================================================
        # REPORTING
        # ====================================================

        if route == "reporting":

            result = handle_reporting(
                database=database,
                payload=payload,
            )

        # ====================================================
        # INTERNAL DOCUMENTS
        # ====================================================

        elif route == "knowledge":

            # Document answers are generated by the
            # streaming endpoint.
            #
            # /ask only performs routing here so we do
            # not generate the same document answer twice.

            result = {
                "success": True,
                "answer": None,
                "report": None,
                "context": None,
                "warnings": [],
                "sources": [],
            }

        # ====================================================
        # NIB PUBLIC WEBSITE
        # ====================================================

        elif route == "web":

            result = handle_web(
                prompt=prompt
            )

        # ====================================================
        # COMPETITOR INTELLIGENCE
        # ====================================================

        elif route == "competitor":

            result = handle_competitor(
                prompt=prompt
            )

        # ====================================================
        # GENERAL CHAT
        #
        # General answers are generated by the streaming
        # endpoint. /ask only performs routing for this route.
        # This avoids generating the same answer twice.
        # ====================================================

        else:

            result = {
                "success": True,
                "answer": None,
                "report": None,
                "context": None,
                "warnings": [],
                "sources": [],
            }

    except ValueError as error:

        return OrchestratorResponse(
            route=route,
            confidence=confidence,
            reason=reason,
            success=False,
            answer=str(
                error
            ),
            report=None,
            context=None,
            warnings=[
                str(error)
            ],
            sources=[],
        )

    except Exception as error:

        return OrchestratorResponse(
            route=route,
            confidence=confidence,
            reason=reason,
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
        )

    return OrchestratorResponse(
        route=route,
        confidence=confidence,
        reason=reason,
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
    )


# ============================================================
# HEALTH
# ============================================================

@router.get(
    "/health"
)
def orchestrator_health():

    return {
        "service":
            "NIBGPT Orchestrator",
        "status":
            "ok",
        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }