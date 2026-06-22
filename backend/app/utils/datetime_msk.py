from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MSK_TZ = ZoneInfo("Europe/Moscow")


def now_msk() -> datetime:
    return datetime.now(MSK_TZ)


def next_calendar_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def base_activation_deadline(period_month: str) -> datetime:
    """15-е число месяца, следующего за периодом начисления, 23:59:59 МСК."""
    year, month = map(int, period_month.split("-"))
    next_year, next_month = next_calendar_month(year, month)
    return datetime(next_year, next_month, 15, 23, 59, 59, tzinfo=MSK_TZ)


def add_working_days(start_date: date, working_days: int) -> date:
    current = start_date
    added = 0
    while added < working_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def compute_activation_deadline(period_month: str, notification_at: datetime) -> datetime:
    """Индивидуальный дедлайн: max(15-е следующего месяца, +5 рабочих дней от уведомления)."""
    base = base_activation_deadline(period_month)
    notify_msk = notification_at.astimezone(MSK_TZ)
    extended = datetime.combine(
        add_working_days(notify_msk.date(), 5),
        time(23, 59, 59),
        tzinfo=MSK_TZ,
    )
    return max(base, extended)


def is_points_deadline_check_day(day: date | None = None) -> bool:
    target = day or now_msk().date()
    return 16 <= target.day <= 21
