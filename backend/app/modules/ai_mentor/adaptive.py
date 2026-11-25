"""Adaptive, rule-based guidance policy for NEXIS AI Mentor.

This module does not train an AI model or inspect individual failed flags.
"""
from __future__ import annotations

import re

FLAG_RE = re.compile(r"(?:NEXIS|CTF|FLAG)\{[^}]*\}|\bflag\s*[:=]\s*\S+", re.I)


def redact(text: str) -> str:
    return FLAG_RE.sub("[redacted]", str(text or ""))


def unlocked_level(attempts: int, previous_hints: int) -> int:
    """Unlock more specific assistance after retries or repeated hints."""
    attempts = max(0, int(attempts))
    previous_hints = max(0, int(previous_hints))
    return min(3, 1 + attempts // 2 + previous_hints // 2)


def choose_level(attempts: int, previous_hints: int, requested: int | None = None) -> int:
    allowed = unlocked_level(attempts, previous_hints)
    if requested is None:
        return allowed
    if requested not in (1, 2, 3):
        raise ValueError("hint_level must be 1, 2, or 3")
    return min(requested, allowed)


def guidance(level: int, category: str, difficulty: str, question: str) -> str:
    """Safe fallback that never includes the hidden writeup or answer."""
    topic = re.sub(r"[^a-zA-Z0-9 _-]", "", category or "cybersecurity")[:50] or "cybersecurity"
    if level == 1:
        body = f"Start by identifying the core {topic} concept in the challenge description."
    elif level == 2:
        body = f"Break this {topic} task into inputs, expected behavior, and evidence; test one hypothesis at a time."
    else:
        body = f"Document what you observed in the {topic} task, compare it with the expected behavior, and revise your next test based on the difference."
    return f"Level {level} ({difficulty}): {body} Avoid submitting random guesses."


def evaluate_progress(attempts: int, hints_used: int, solved: bool) -> dict:
    attempts = max(0, int(attempts))
    hints_used = max(0, int(hints_used))
    if solved:
        feedback = "Solved. Review which observation led to the correct solution and how you verified it."
        next_steps = ["Summarize the successful reasoning", "Review a related defensive concept"]
    elif attempts == 0:
        feedback = "No flag attempts recorded. Read the challenge carefully and identify the first testable hypothesis."
        next_steps = ["Inspect the challenge description", "Attempt one reasoned test"]
    else:
        feedback = "No successful submission recorded. Revisit assumptions and compare each test with observed evidence."
        next_steps = ["Review the concepts relevant to this challenge", "Change one variable at a time before retrying"]
    if attempts >= 4 and not solved:
        feedback += " Several attempts were made; focus on method rather than guessing."
    if hints_used >= 2:
        next_steps.append("Explain the hint in your own words before your next attempt")
    return {"feedback": feedback, "next_steps": next_steps, "progress_status": "solved" if solved else ("attempted" if attempts else "not_attempted"), "feedback_mode": "rule-based-behavioral"}
