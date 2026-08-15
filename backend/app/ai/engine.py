from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.data_source import DataSource


def generate_nibgpt_response(
    database: Session,
    prompt: str,
) -> tuple[str, str]:
    normalized_prompt = prompt.strip().lower()

    if any(
        phrase in normalized_prompt
        for phrase in [
            "hello",
            "hi ",
            "good morning",
            "good afternoon",
            "good evening",
        ]
    ) or normalized_prompt in {"hi", "hello"}:
        return (
            (
                "Hello. I am NIBGPT, NIB International Bank's "
                "internal artificial intelligence workspace.\n\n"
                "I can currently help you review registered data "
                "sources and understand the capabilities being built "
                "into the platform."
            ),
            "system",
        )

    if (
        "data source" in normalized_prompt
        or "database" in normalized_prompt
        or "connections" in normalized_prompt
    ):
        total_statement = select(
            func.count(DataSource.id)
        )

        connected_statement = select(
            func.count(DataSource.id)
        ).where(
            DataSource.status == "connected"
        )

        active_statement = select(
            func.count(DataSource.id)
        ).where(
            DataSource.is_active.is_(True)
        )

        total = database.scalar(total_statement) or 0
        connected = database.scalar(connected_statement) or 0
        active = database.scalar(active_statement) or 0

        sources_statement = (
            select(DataSource)
            .where(DataSource.is_active.is_(True))
            .order_by(DataSource.name)
        )

        sources = list(
            database.scalars(sources_statement).all()
        )

        if not sources:
            return (
                (
                    "There are currently no active data sources "
                    "registered in NIBGPT.\n\n"
                    "An administrator can add Oracle, MySQL or "
                    "PostgreSQL connections from the Data Sources module."
                ),
                "data_sources",
            )

        source_lines = []

        for source in sources:
            status_label = (
                "Connected"
                if source.status == "connected"
                else (
                    "Failed"
                    if source.status == "failed"
                    else "Not tested"
                )
            )

            source_lines.append(
                f"• {source.name} — "
                f"{source.database_type.upper()} — "
                f"{status_label}"
            )

        response = (
            "NIBGPT Data Source Summary\n\n"
            f"Total registered: {total}\n"
            f"Active: {active}\n"
            f"Connected: {connected}\n\n"
            "Active sources:\n"
            + "\n".join(source_lines)
        )

        return response, "data_sources"

    if (
        "what can you do" in normalized_prompt
        or "capabilities" in normalized_prompt
        or "help me" in normalized_prompt
    ):
        return (
            (
                "Current NIBGPT capabilities:\n\n"
                "• Secure user authentication\n"
                "• Encrypted database connection management\n"
                "• Oracle, MySQL and PostgreSQL connection testing\n"
                "• Conversation and message history\n"
                "• Institutional AI workspace\n\n"
                "Planned capabilities include document intelligence, "
                "prompt-based reporting, metadata-aware database access, "
                "secure SQL generation and NIB-owned model inference."
            ),
            "system",
        )

    if (
        "report" in normalized_prompt
        or "deposit" in normalized_prompt
        or "loan" in normalized_prompt
        or "branch" in normalized_prompt
    ):
        return (
            (
                "I understand that this appears to be a banking reporting "
                "request. The report engine is not connected yet.\n\n"
                "To support this request safely, NIBGPT will need:\n"
                "1. An approved data source\n"
                "2. Database metadata and business definitions\n"
                "3. A read-only reporting user\n"
                "4. An approved report template or validated SQL rule\n\n"
                "This capability will be added in the Prompt Reports phase."
            ),
            "report_request",
        )

    return (
        (
            "Your prompt was received and saved successfully.\n\n"
            "The NIB-owned language model is not connected yet, so I will "
            "not generate an unsupported answer. As we build the knowledge, "
            "reporting and model layers, this workspace will answer using "
            "approved NIB information and provide source traceability."
        ),
        "unclassified",
    )
