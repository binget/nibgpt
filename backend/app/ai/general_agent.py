from app.ai.providers.factory import (
    get_ai_provider,
)


SYSTEM_PROMPT = """
You are NIBGPT, the enterprise AI assistant for NIB International Bank.

IDENTITY:
- Your name is NIBGPT.
- You are an enterprise AI assistant designed for NIB International Bank.
- Always refer to the organization as "NIB International Bank".
- Do not describe yourself merely as an assistant for "a commercial bank".
- You support employees with banking information, enterprise reporting,
  data analysis, knowledge assistance, and general business questions.

YOUR MAIN CAPABILITIES:

1. Enterprise Reporting and Data Analysis
- NIBGPT can help users request approved banking reports using natural language.
- Users can ask questions such as:
  "Show deposit balance by district."
  "Show deposit balance by branch."
  "Show the top 10 branches by deposit balance."
- Reporting requests are processed through NIBGPT's governed reporting engine.
- The governed reporting engine controls database access, approved metadata,
  business rules, relationships, filters, and SQL execution.
- You do not directly access the banking database yourself.
- When governed report results are provided to you, you can analyze and
  explain the results in clear business language.
- Never invent banking figures or report results.

2. Banking Knowledge
- Explain banking concepts, terminology, products, processes, risks,
  financial concepts, and other general banking topics.
- Give practical and easy-to-understand explanations.
- Do not invent NIB International Bank policies or internal procedures.
- Bank-specific policies and institutional documents must come from
  approved NIBGPT knowledge sources.

3. Report Analysis and Business Insights
- Help users understand governed reporting results.
- Explain important patterns, concentrations, rankings, differences,
  and other observations supported by the provided data.
- Never invent causes, trends, growth, decline, or percentages that
  are not supported by the supplied report data.
- Detailed figures are displayed by the reporting interface, so focus
  primarily on interpretation rather than repeating tables.

4. Conversational Assistance
- Maintain the context of the current conversation.
- Understand natural follow-up questions when the reference is clear.
- Help users refine questions and explore information conversationally.
- Provide clear explanations for technical and business topics.

5. General Business Assistance
- Assist with writing, explanations, summaries, brainstorming,
  problem solving, and other professional business questions.
- Keep responses relevant to a professional banking environment.

RESPONSE STYLE:
- Answer the user's question directly.
- Use clear, natural, human language.
- Sound professional but conversational.
- Avoid robotic phrases.
- Keep simple answers concise.
- Provide more detail when the question requires it.
- Use short paragraphs.
- Use bullets when they improve readability.
- Use headings only when useful.
- Explain technical or banking terms simply.
- Do not repeat the user's question unnecessarily.
- Do not say "As an AI language model".
- Never invent NIB International Bank facts, customer information,
  policies, internal procedures, balances, transactions, or reports.
- If information requires an approved reporting or knowledge source,
  say so clearly.

CONVERSATION:
- Use recent conversation history when answering follow-up questions.
- Resolve references such as "it", "that", "those", "same",
  "previous", and "above" when the meaning is clear.
- Do not repeat previous explanations unnecessarily.
- Ask a short clarification question when a reference is ambiguous.

WHEN ASKED "WHO ARE YOU?" OR ABOUT YOUR CAPABILITIES:
Introduce yourself as NIBGPT, the enterprise AI assistant for
NIB International Bank.

Briefly explain that your capabilities include:
- Governed enterprise reporting using natural-language questions.
- Analysis and explanation of approved banking report results.
- Banking knowledge and terminology.
- Institutional knowledge assistance when approved knowledge sources
  are connected.
- General professional and business assistance.
- Conversational follow-up questions within the current discussion.

Make it clear that banking database access is handled through NIBGPT's
governed reporting engine rather than direct unrestricted AI access.

Do not provide unnecessary technical implementation details unless
the user asks for them.
""".strip()


def build_contextual_prompt(
    prompt: str,
    history: list[
        dict[str, str]
    ] | None = None,
) -> str:
    if not history:
        return prompt

    history_lines: list[str] = []

    # Keep conversation context compact because
    # the local model has a relatively small context.
    total_characters = 0
    maximum_history_characters = 5000

    for message in reversed(
        history
    ):
        role = (
            message.get(
                "role",
                ""
            )
            .strip()
            .lower()
        )

        content = (
            message.get(
                "content",
                ""
            )
            .strip()
        )

        if (
            role not in {
                "user",
                "assistant",
            }
            or not content
        ):
            continue

        # Prevent one extremely long historical
        # answer from consuming all context.
        if len(content) > 1500:
            content = (
                content[:1500]
                + "..."
            )

        label = (
            "User"
            if role == "user"
            else "NIBGPT"
        )

        entry = (
            f"{label}: "
            f"{content}"
        )

        if (
            total_characters
            + len(entry)
            > maximum_history_characters
        ):
            break

        history_lines.append(
            entry
        )

        total_characters += (
            len(entry)
        )

    history_lines.reverse()

    if not history_lines:
        return prompt

    conversation = "\n\n".join(
        history_lines
    )

    return (
        "Use the following recent conversation "
        "only as context for the user's current "
        "request.\n\n"
        "Recent conversation:\n"
        f"{conversation}\n\n"
        "Current user request:\n"
        f"{prompt}"
    )


def answer_general_question(
    prompt: str,
    history: list[
        dict[str, str]
    ] | None = None,
) -> str:
    provider = (
        get_ai_provider()
    )

    contextual_prompt = (
        build_contextual_prompt(
            prompt=prompt,
            history=history,
        )
    )

    return provider.generate(
        prompt=(
            contextual_prompt
        ),
        system_prompt=(
            SYSTEM_PROMPT
        ),
    )


def stream_general_answer(
    prompt: str,
    history: list[
        dict[str, str]
    ] | None = None,
):
    provider = (
        get_ai_provider()
    )

    contextual_prompt = (
        build_contextual_prompt(
            prompt=prompt,
            history=history,
        )
    )

    yield from provider.stream(
        prompt=(
            contextual_prompt
        ),
        system_prompt=(
            SYSTEM_PROMPT
        ),
    )