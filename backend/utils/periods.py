"""Calendar-month period helpers — periods are 'YYYY-MM' strings.

Shared rather than per-app because the explorer tabs pad their chart axes the
same way: every month in the requested window is emitted, gaps carrying null,
so a missing month reads as a gap instead of shifting the axis. `month_range`
started in v1_weather; v1_publication needs the same thing, and calendar
arithmetic belongs to neither app.
"""
from datetime import date, datetime


def month_start(period: str) -> date:
    """'YYYY-MM' -> the first of that month, for ORM date filters."""
    return datetime.strptime(f"{period}-01", "%Y-%m-%d").date()


def shift_period(period: str, months: int) -> str:
    """'2026-05' shifted by N months, N negative to go back."""
    year, month = map(int, period.split("-"))
    total = year * 12 + month - 1 + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def period_span(from_period: str, to_period: str) -> int:
    """Months in the inclusive window; zero or negative when reversed."""
    from_year, from_month = map(int, from_period.split("-"))
    to_year, to_month = map(int, to_period.split("-"))
    return (to_year - from_year) * 12 + to_month - from_month + 1


def month_range(from_period: str, to_period: str) -> list:
    """Inclusive list of 'YYYY-MM' periods; empty when reversed."""
    return [
        shift_period(from_period, offset)
        for offset in range(max(period_span(from_period, to_period), 0))
    ]
