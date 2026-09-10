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

from app.core.auth_dependencies import get_current_user
from app.models.user import User

from app.services.authorization_service import (
    resolve_authorization_requirement,
)

from app.services.rbac_service import (
    authorize_request,
    get_user_data_scopes,
    get_user_governance_role,
)

from app.ai.forecast_engine import (
    build_forecast_history_prompt,
    extract_forecast_subject,
    forecast_from_reporting_result,
    is_forecast_request,
)

from app.services.semantic_time_series_cache import (
    build_scope_signature,
    build_signature,
    cached_series_to_rows,
    get_cached_series_by_signature,
    upsert_series,
)

from app.models.business_measure import BusinessMeasure

from app.ai.forecast_engine import (
    build_forecast_history_prompt,
    extract_forecast_subject,
    forecast_from_reporting_result,
    is_forecast_request,
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
    current_user: User,
) -> list[dict[str, str]]:

    if conversation_id is None:
        return []

    conversation = database.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
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
        "decision": result.get(
            "decision"
        ),
        "warnings": warnings,
        "errors": (
            result.get(
                "errors"
            )
            or []
        ),
        "explanation": (
            result.get(
                "explanation"
            )
            or []
        ),
        "sources": (
            result.get(
                "sources"
            )
            or []
        ),
}


def resolve_forecast_measure_id(
    database: Session,
    prompt: str,
) -> int | None:
    """
    Resolve a forecast subject against the semantic catalog.

    This is intentionally generic. It searches measure name,
    synonyms and trigger phrases instead of hardcoding deposit,
    account opening, loan, etc.
    """

    subject = (
        extract_forecast_subject(prompt)
        or ""
    ).lower().strip()

    if not subject:
        return None

    subject_tokens = {
        token
        for token in subject.split()
        if len(token) >= 3
    }

    measures = (
        database.query(BusinessMeasure)
        .filter(
            BusinessMeasure.is_active.is_(True)
        )
        .all()
    )

    best_measure = None
    best_score = 0

    for measure in measures:
        searchable = " ".join(
            [
                measure.name or "",
                measure.synonyms or "",
                measure.trigger_phrases or "",
                measure.description or "",
            ]
        ).lower()

        score = sum(
            1
            for token in subject_tokens
            if token in searchable
        )

        # Strong preference for direct phrase match.
        if subject in searchable:
            score += 10

        if score > best_score:
            best_score = score
            best_measure = measure

    if (
        best_measure is None
        or best_score <= 0
    ):
        return None

    return best_measure.id

# ============================================================
# REPORTING
# ============================================================

def handle_reporting(
    database: Session,
    payload: OrchestratorRequest,
    governance_role: str,
    branch_scope_value: str | None,
    allow_confidential_aggregate: bool,
) -> dict:

    (
        reporting_prompt,
        reporting_context,
    ) = prepare_reporting_prompt(
        payload
    )

    forecast_request = is_forecast_request(
        payload.prompt
    )

    # ========================================================
    # NORMAL REPORTING
    # ========================================================

    if not forecast_request:
        result = execute_governed_prompt(
            database=database,
            prompt=reporting_prompt,
            domain_id=None,
            requested_limit=payload.requested_limit,
            maximum_entities=payload.maximum_entities,
            maximum_path_depth=payload.maximum_path_depth,
            user_role=governance_role,
            branch_scope_value=branch_scope_value,
            allow_confidential_aggregate=(
                allow_confidential_aggregate
            ),
        )

        return normalize_reporting_result(
            result=result,
            context=reporting_context,
        )

    # ========================================================
    # FORECAST
    # ========================================================

    history_prompt = (
        build_forecast_history_prompt(
            payload.prompt
        )
    )

    scope_signature = (
        build_scope_signature(
            governance_role=governance_role,
            branch_scope_value=branch_scope_value,
        )
    )

    history_signature = build_signature(
        {
            "prompt": history_prompt.lower().strip(),
        }
    )

    # --------------------------------------------------------
    # 1. CHECK POSTGRESQL CACHE FIRST
    # --------------------------------------------------------

    cached_series = (
        get_cached_series_by_signature(
            database=database,
            period_grain="month",
            filter_signature=history_signature,
            scope_signature=scope_signature,
        )
    )

    if len(cached_series) >= 4:

        measure_name = (
            extract_forecast_subject(
                payload.prompt
            )
            or "Value"
        ).title()

        cached_rows = (
            cached_series_to_rows(
                cached_series,
                period_column="Period",
                value_column=measure_name,
            )
        )

        cached_result = {
            "success": True,
            "rows": cached_rows,
            "columns": [
                "Period",
                measure_name,
            ],
            "row_count": len(
                cached_rows
            ),
            "warnings": [],
            "errors": [],
            "sources": [],
            "cache_status": "hit",
        }

        result = (
            forecast_from_reporting_result(
                result=cached_result,
                forecast_prompt=payload.prompt,
            )
        )

        result["cache_status"] = "hit"

        return normalize_reporting_result(
            result=result,
            context=reporting_context,
        )

    # --------------------------------------------------------
    # 2. CACHE MISS -> USE GOVERNED REPORTING
    # --------------------------------------------------------

    result = execute_governed_prompt(
        database=database,
        prompt=history_prompt,
        domain_id=None,
        requested_limit=payload.requested_limit,
        maximum_entities=payload.maximum_entities,
        maximum_path_depth=payload.maximum_path_depth,
        user_role=governance_role,
        branch_scope_value=branch_scope_value,
        allow_confidential_aggregate=(
            allow_confidential_aggregate
        ),
    )

    # --------------------------------------------------------
    # 3. SAVE VERIFIED HISTORY INTO CACHE
    # --------------------------------------------------------

    if (
        isinstance(result, dict)
        and result.get("success")
    ):
        rows = list(
            result.get("rows")
            or []
        )

        if rows:
            first_row = rows[0]

            period_column = None
            value_column = None

            for column in first_row.keys():
                normalized = str(
                    column
                ).lower()

                if (
                    "period" in normalized
                    or "month" in normalized
                    or "date" in normalized
                    or "procdate" in normalized
                    or "opening" in normalized
                ):
                    period_column = column
                    break

            if period_column is None:
                period_column = next(
                    iter(first_row.keys()),
                    None,
                )

            for column in first_row.keys():
                if column == period_column:
                    continue

                sample_value = first_row.get(
                    column
                )

                try:
                    float(
                        str(sample_value).replace(
                            ",",
                            "",
                        )
                    )
                    value_column = column
                    break
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            measure_id = (
                resolve_forecast_measure_id(
                    database=database,
                    prompt=payload.prompt,
                )
            )

            if (
                measure_id is not None
                and period_column is not None
                and value_column is not None
            ):
                upsert_series(
                    database=database,
                    business_measure_id=measure_id,
                    period_grain="month",
                    rows=rows,
                    period_column=period_column,
                    value_column=value_column,
                    dimension_signature="none",
                    filter_signature=history_signature,
                    scope_signature=scope_signature,
                    source_table="governed_reporting",
                    commit=True,
                )

                result["cache_status"] = "stored"

    # --------------------------------------------------------
    # 4. FORECAST FROM VERIFIED HISTORY
    # --------------------------------------------------------

    result = forecast_from_reporting_result(
        result=result,
        forecast_prompt=payload.prompt,
    )

    result["cache_status"] = (
        result.get("cache_status")
        or "miss"
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

    history = load_conversation_history(
        database=database,
        conversation_id=payload.conversation_id,
        current_prompt=prompt,
        current_user=current_user,
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
    current_user: User = Depends(
        get_current_user
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
        
            # ========================================================
        # AUTHORIZATION GATE
        #
        # This MUST execute before any route handler.
        # No reporting/document/tool/data-source execution may
        # happen before this check succeeds.
        # ========================================================

        authorization = (
            resolve_authorization_requirement(
                prompt=prompt,
                route=route,
            )
        )

        authorize_request(
            database=database,
            user=current_user,
            permission_code=(
                authorization.permission_code
            ),
            resource=(
                authorization.resource
            ),
            request_text=prompt,
        )
        
        allow_confidential_aggregate = (
            authorization.permission_code
            in {
                "deposit.summary.view",
                "deposit.forecast.view",
                "account_opening.analytics.view",
                "account_opening.forecast.view",
            }
        )
        
        governance_role = (
            get_user_governance_role(
                database=database,
                user_id=current_user.id,
            )
        )
        
        user_scopes = get_user_data_scopes(
            database=database,
            user_id=current_user.id,
        )

        has_enterprise_scope = any(
            scope.scope_type == "enterprise"
            and scope.scope_value == "*"
            for scope in user_scopes
        )

        branch_scope_value = None

        if not has_enterprise_scope:
            branch_scopes = [
                scope.scope_value
                for scope in user_scopes
                if (
                    scope.scope_type == "branch"
                    and scope.scope_value
                )
            ]

            if branch_scopes:
                branch_scope_value = branch_scopes[0]


    try:

        # ====================================================
        # REPORTING
        # ====================================================

        if route == "reporting":

            result = handle_reporting(
                database=database,
                payload=payload,
                governance_role=governance_role,
                branch_scope_value=branch_scope_value,
                allow_confidential_aggregate=(
                    allow_confidential_aggregate
                ),
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
        decision=result.get(
            "decision"
        ),
        errors=result.get(
            "errors",
            [],
        ),
        explanation=result.get(
            "explanation",
            [],
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