import re
from typing import Literal

from models.schemas import SearchFilters

AdvisingFocus = Literal["PHYS", "ECE"]

_COMPARISON_RE = re.compile(
    r"\b(which|better|best|good|choose|pick|recommend|should|right\s+for\s+me|good\s+for\s+me)\b",
    re.IGNORECASE,
)
_PHYS_RE = re.compile(r"\b(physics|phys)\b", re.IGNORECASE)
_ECE_RE = re.compile(r"\b(electrical|electrical engineering|ece|ee)\b", re.IGNORECASE)
_ADVICE_PROMPT_RE = re.compile(
    r"\b(before i recommend|before recommending|tell me a bit|tell me your|i should know|need a bit more)\b",
    re.IGNORECASE,
)

_ECE_SIGNALS = {
    "ai": 2,
    "artificial intelligence": 2,
    "build": 2,
    "building": 2,
    "chip": 3,
    "chips": 3,
    "circuit": 3,
    "circuits": 3,
    "coding": 2,
    "computer": 2,
    "embedded": 3,
    "electronics": 3,
    "hardware": 3,
    "industry": 2,
    "machine learning": 2,
    "programming": 2,
    "robotics": 2,
    "semiconductor": 3,
    "semiconductors": 3,
    "signals": 2,
    "software": 2,
    "systems": 2,
}

_PHYS_SIGNALS = {
    "academia": 2,
    "astronomy": 3,
    "astrophysics": 3,
    "fundamental": 3,
    "fundamentals": 3,
    "grad school": 2,
    "math": 1,
    "mechanics": 2,
    "particle": 2,
    "phd": 2,
    "physics research": 3,
    "quantum": 3,
    "research": 2,
    "science": 2,
    "theoretical": 3,
    "theory": 3,
}

_PREFERENCE_RE = re.compile(
    r"\b(i like|i love|interested in|interest|career|job|research|build|coding|programming|"
    r"hardware|circuits?|electronics|theory|theoretical|quantum|math|ai|machine learning|"
    r"robotics|semiconductor|grad school|phd|industry|hands-on|hands on)\b",
    re.IGNORECASE,
)


def needs_advising_clarification(query: str, history: list[dict], filters: SearchFilters) -> bool:
    return is_physics_ece_advising_query(query, filters) and advising_focus(query, history) is None


def is_pending_advising_followup(query: str, history: list[dict]) -> bool:
    if not _has_recent_physics_ece_advising_context(history):
        return False
    return bool(_PREFERENCE_RE.search(query))


def is_physics_ece_advising_query(query: str, filters: SearchFilters | None = None) -> bool:
    if not _mentions_physics_and_ece(query, filters):
        return False
    return bool(_COMPARISON_RE.search(query))


def advising_focus(query: str, history: list[dict] | None = None) -> AdvisingFocus | None:
    text = _user_preference_text(query, history or [])
    ece_score = _score_text(text, _ECE_SIGNALS)
    phys_score = _score_text(text, _PHYS_SIGNALS)

    if ece_score >= phys_score + 2 and ece_score >= 2:
        return "ECE"
    if phys_score >= ece_score + 2 and phys_score >= 2:
        return "PHYS"
    return None


def advising_clarification_response() -> str:
    return (
        "I can help you choose between Physics and Electrical/ECE, but I should know more about you before recommending one. "
        "Are you more excited by fundamental science and research, or by building circuits, hardware, software, and systems? "
        "Tell me your career goal, favorite type of work, and comfort with math/programming."
    )


def advising_subject_for_focus(focus: AdvisingFocus) -> str:
    return focus


def _mentions_physics_and_ece(query: str, filters: SearchFilters | None) -> bool:
    if filters and filters.subject:
        subjects = {part.strip().upper() for part in filters.subject.split("|")}
        if {"PHYS", "ECE"} <= subjects:
            return True

    return bool(_PHYS_RE.search(query) and _ECE_RE.search(query))


def _has_recent_physics_ece_advising_context(history: list[dict]) -> bool:
    for message in history[-6:]:
        content = str(message.get("content") or "")
        role = str(message.get("role") or "")
        if role == "assistant" and _ADVICE_PROMPT_RE.search(content):
            return True
        if role == "user" and _PHYS_RE.search(content) and _ECE_RE.search(content) and _COMPARISON_RE.search(content):
            return True
    return False


def _user_preference_text(query: str, history: list[dict]) -> str:
    parts = [
        str(message.get("content") or "")
        for message in history[-6:]
        if message.get("role") == "user"
    ]
    parts.append(query)
    return " ".join(parts).lower()


def _score_text(text: str, signals: dict[str, int]) -> int:
    score = 0
    for phrase, weight in signals.items():
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            score += weight
    return score
