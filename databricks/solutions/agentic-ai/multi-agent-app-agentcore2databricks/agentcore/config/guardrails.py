"""
AgentCore guardrail definitions.
Applied to the Supervisor and Synthesizer agents on the AWS side.
"""

import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|all)\s+instructions",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"forget\s+(your|all)\s+instructions",
    r"override\s+safety",
    r"jailbreak",
]

OFF_TOPIC_PATTERNS = [
    r"write\s+(me\s+)?(a\s+)?(poem|story|song|essay)",
    r"(hack|exploit|attack)\s+",
    r"(how\s+to\s+)?(make|build|create)\s+(a\s+)?(bomb|weapon|virus)",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
]

_injection_re = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)
_offtopic_re = re.compile("|".join(OFF_TOPIC_PATTERNS), re.IGNORECASE)
_pii_re = re.compile("|".join(PII_PATTERNS))


def check_input_guardrails(text: str) -> tuple[bool, str]:
    if _injection_re.search(text):
        return False, "Input blocked: potential prompt injection detected."
    if _offtopic_re.search(text):
        return False, "Input blocked: request is outside the financial analysis domain."
    return True, ""


def check_output_guardrails(text: str) -> tuple[bool, str]:
    if _pii_re.search(text):
        return False, "Output blocked: potential PII detected in response."
    return True, ""
