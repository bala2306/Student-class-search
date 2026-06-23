import re


class SecurityViolation(ValueError):
    pass


MAX_QUERY_CHARS = 800
MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CHARS = 1200

COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4})\s*[- ]?\s*(\d{3})\b", re.IGNORECASE)
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$")

SAFE_DAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}
DAY_ALIASES = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}

PROMPT_ATTACK_RE = re.compile(
    r"("
    r"ignore\s+(?:all\s+)?(?:previous|prior|above|system|developer)\s+instructions"
    r"|disregard\s+(?:all\s+)?(?:previous|prior|above|system|developer)\s+instructions"
    r"|override\s+(?:the\s+)?(?:system|developer|safety)\s+(?:prompt|instructions)"
    r"|reveal\s+(?:the\s+)?(?:system|developer|hidden)\s+(?:prompt|instructions|message)"
    r"|show\s+(?:me\s+)?(?:the\s+)?(?:system|developer|hidden)\s+(?:prompt|instructions|message)"
    r"|print\s+(?:the\s+)?(?:system|developer|hidden)\s+(?:prompt|instructions|message)"
    r"|dump\s+(?:the\s+)?(?:system|developer|hidden)\s+(?:prompt|instructions|message)"
    r"|what\s+(?:is|are)\s+your\s+(?:system|developer|hidden)\s+(?:prompt|instructions)"
    r"|api[_\s-]?key|openai[_\s-]?api[_\s-]?key|neo4j[_\s-]?password|supabase[_\s-]?key"
    r"|\.env\b|environment\s+variables?"
    r")",
    re.IGNORECASE,
)

DESTRUCTIVE_DB_RE = re.compile(
    r"\b("
    r"drop\s+table|truncate\s+table|delete\s+from|insert\s+into|update\s+\w+\s+set"
    r"|alter\s+table|create\s+table|grant\s+|revoke\s+|detach\s+delete"
    r"|match\s*\(.+\)\s*delete|merge\s*\(.+\)\s*set"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)


def validate_user_query(query: str) -> str:
    cleaned = _strip_control_chars(query).strip()
    if len(cleaned) < 2:
        raise SecurityViolation("Query too short. Please enter at least 2 characters.")
    if len(cleaned) > MAX_QUERY_CHARS:
        raise SecurityViolation(f"Query too long. Please keep it under {MAX_QUERY_CHARS} characters.")
    if _looks_unsafe(cleaned):
        raise SecurityViolation("That request is outside the course-search scope.")
    return cleaned


def sanitize_history(history: list[dict]) -> list[dict]:
    safe_history: list[dict] = []
    for message in history[-MAX_HISTORY_MESSAGES:]:
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue

        content = _strip_control_chars(str(message.get("content") or "")).strip()
        if not content or _looks_unsafe(content):
            continue
        safe_history.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return safe_history


def safe_like_term(value: str | None, max_chars: int = 80) -> str | None:
    if value is None:
        return None

    cleaned = _strip_control_chars(str(value))
    cleaned = cleaned.replace("%", " ").replace("*", " ")
    cleaned = re.sub(r"[,(){}\[\];:'\"\\|]", " ", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9 #&+/_-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._-/")
    if not cleaned:
        return None
    return cleaned[:max_chars].strip()


def validate_course_code(value: str) -> str:
    match = COURSE_CODE_RE.search(value or "")
    if not match:
        raise SecurityViolation("Invalid course code.")
    return f"{match.group(1).upper()}{match.group(2)}"


def validate_day(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _strip_control_chars(value).strip()
    cleaned = DAY_ALIASES.get(cleaned.lower(), cleaned.capitalize())
    if cleaned not in SAFE_DAYS:
        raise SecurityViolation("Invalid day filter.")
    return cleaned


def validate_time(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _strip_control_chars(value).strip()
    if not TIME_RE.match(cleaned):
        raise SecurityViolation("Invalid time filter.")
    return cleaned[:5]


def _looks_unsafe(text: str) -> bool:
    return bool(PROMPT_ATTACK_RE.search(text) or DESTRUCTIVE_DB_RE.search(text))


def _strip_control_chars(value: str) -> str:
    return "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
