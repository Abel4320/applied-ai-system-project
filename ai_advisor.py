import json
from datetime import datetime, timezone
from pathlib import Path

KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"
LOGS_DIR = Path(__file__).parent / "logs"
VALID_SPECIES = {"dog", "cat", "rabbit", "bird", "other"}


def _load_file(species: str) -> tuple[list[str], bool]:
    """Return (lines, fallback_used)."""
    species = species.lower()
    fallback_used = species not in VALID_SPECIES
    if fallback_used:
        species = "other"
    file_path = KNOWLEDGE_BASE_DIR / f"{species}.txt"
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()], fallback_used


def _keyword_search(lines: list[str], keywords: list[str]) -> list[str]:
    if not keywords:
        return lines
    matched = [
        line for line in lines
        if any(kw.lower() in line.lower() for kw in keywords)
    ]
    return matched if matched else lines


def _log(species: str, task_types: list[str], num_tips: int, confidence: float, fallback_used: bool) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "species": species,
        "task_types": task_types,
        "num_tips": num_tips,
        "confidence": round(confidence, 2),
        "fallback_used": fallback_used,
    }
    with open(LOGS_DIR / "ai_interactions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_care_tips(species: str, task_types: list[str] | None = None) -> tuple[str, float]:
    """Retrieve care tips for a species filtered by task types.

    Args:
        species: Pet species (dog, cat, rabbit, bird, other).
        task_types: List of task type strings to filter tips (e.g. ["walk", "feeding"]).

    Returns:
        A tuple of (formatted tips string, confidence score 0.0–1.0).
        Confidence = matched lines / total lines. 1.0 when no filter is applied.
    """
    lines, fallback_used = _load_file(species)
    keywords = [t.lower() for t in task_types] if task_types else []
    matched = _keyword_search(lines, keywords)

    if not keywords:
        confidence = 1.0
    elif len(lines) == 0:
        confidence = 0.0
    else:
        explicitly_matched = [
            line for line in lines
            if any(kw.lower() in line.lower() for kw in keywords)
        ]
        confidence = len(explicitly_matched) / len(lines)

    tips = [line.split(":", 1)[1].strip() if ":" in line else line for line in matched]
    result = "\n".join(f"• {tip}" for tip in tips)

    _log(species, keywords, len(tips), confidence, fallback_used)

    return result, confidence
