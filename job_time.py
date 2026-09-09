"""Helpers for validating and displaying Upwork job posting times."""
from __future__ import annotations

from datetime import datetime, timezone


DATE_FIELDS = ("published_date", "created_date", "published_on", "created_on")


def published_at(job: dict) -> datetime | None:
    """Return the first valid UTC posting timestamp supplied by Upwork."""
    for field in DATE_FIELDS:
        value = job.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def is_recent(job: dict, max_age_minutes: int, now: datetime | None = None) -> bool:
    """Only accept jobs with a valid timestamp inside the freshness window."""
    posted = published_at(job)
    if posted is None:
        return False
    current = now or datetime.now(timezone.utc)
    age_seconds = (current - posted).total_seconds()
    return -3600 <= age_seconds <= max_age_minutes * 60


def published_timestamp(job: dict) -> float:
    """Sortable posting timestamp; missing/invalid timestamps sort last."""
    posted = published_at(job)
    return posted.timestamp() if posted else 0.0


def age_label(job: dict, now: datetime | None = None) -> str:
    """Return a compact human-readable posting age for alert emails."""
    posted = published_at(job)
    if posted is None:
        return "time unavailable"
    current = now or datetime.now(timezone.utc)
    seconds = max(0, int((current - posted).total_seconds()))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hr ago"
    days = seconds // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"
