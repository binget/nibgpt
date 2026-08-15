import re
from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str
    confidence: int
    is_safe: bool
    blocked_reason: str | None
    matched_phrases: list[str]


BLOCKED_PATTERNS = {
    "delete": [
        r"\bdelete\b",
        r"\bremove\b",
        r"\bdrop\b",
        r"\btruncate\b",
        r"\berase\b",
    ],
    "update": [
        r"\bupdate\b",
        r"\bchange\b",
        r"\bmodify\b",
        r"\bedit\b",
        r"\bset\b.+\bto\b",
    ],
    "insert": [
        r"\binsert\b",
        r"\bcreate record\b",
        r"\badd record\b",
        r"\bsave into\b",
    ],
}


INTENT_PATTERNS = {
    "count": [
        r"\bhow many\b",
        r"\bcount\b",
        r"\bnumber of\b",
        r"\btotal number\b",
    ],
    "ranking": [
        r"\btop\s+\d+\b",
        r"\bbottom\s+\d+\b",
        r"\bhighest\b",
        r"\blowest\b",
        r"\blargest\b",
        r"\bsmallest\b",
        r"\brank\b",
    ],
    "trend": [
        r"\btrend\b",
        r"\bover time\b",
        r"\bmonthly\b",
        r"\bweekly\b",
        r"\bdaily\b",
        r"\byearly\b",
        r"\bgrowth\b",
        r"\bdecline\b",
    ],
    "comparison": [
        r"\bcompare\b",
        r"\bversus\b",
        r"\bvs\b",
        r"\bdifference between\b",
    ],
    "expiry_monitoring": [
        r"\bexpired\b",
        r"\bexpiring\b",
        r"\bexpiry\b",
        r"\boverdue\b",
        r"\bdue soon\b",
    ],
    "aggregation": [
        r"\btotal\b",
        r"\bsum\b",
        r"\baverage\b",
        r"\bavg\b",
        r"\bminimum\b",
        r"\bmaximum\b",
        r"\bmin\b",
        r"\bmax\b",
    ],
    "select": [
        r"\bshow\b",
        r"\blist\b",
        r"\bfind\b",
        r"\bdisplay\b",
        r"\bgive me\b",
        r"\bwhich\b",
        r"\bwhat are\b",
    ],
}


INTENT_PRIORITY = [
    "count",
    "ranking",
    "trend",
    "comparison",
    "expiry_monitoring",
    "aggregation",
    "select",
]


def normalize_prompt(prompt: str) -> str:
    normalized = prompt.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized


def find_matches(
    normalized_prompt: str,
    patterns: list[str],
) -> list[str]:
    matches: list[str] = []

    for pattern in patterns:
        result = re.search(
            pattern,
            normalized_prompt,
        )

        if result:
            matches.append(
                result.group(0)
            )

    return list(dict.fromkeys(matches))


def detect_intent(prompt: str) -> IntentResult:
    normalized_prompt = normalize_prompt(prompt)

    for operation, patterns in BLOCKED_PATTERNS.items():
        matches = find_matches(
            normalized_prompt,
            patterns,
        )

        if matches:
            return IntentResult(
                intent="blocked",
                confidence=100,
                is_safe=False,
                blocked_reason=(
                    f"Write operation detected: {operation}. "
                    "NIBGPT only permits read-only reporting requests."
                ),
                matched_phrases=matches,
            )

    for intent in INTENT_PRIORITY:
        matches = find_matches(
            normalized_prompt,
            INTENT_PATTERNS[intent],
        )

        if not matches:
            continue

        base_confidence = {
            "count": 98,
            "ranking": 96,
            "trend": 94,
            "comparison": 94,
            "expiry_monitoring": 96,
            "aggregation": 94,
            "select": 88,
        }[intent]

        return IntentResult(
            intent=intent,
            confidence=base_confidence,
            is_safe=True,
            blocked_reason=None,
            matched_phrases=matches,
        )

    return IntentResult(
        intent="unknown",
        confidence=40,
        is_safe=True,
        blocked_reason=None,
        matched_phrases=[],
    )
