import calendar
from datetime import date


DEFAULT_WARNING_MONTHS = 5


def add_calendar_months(source_date, months):
    """Add calendar months, using the target month's final day when needed."""
    if months < 0:
        raise ValueError('Months must not be negative')
    target_index = source_date.month - 1 + months
    target_year = source_date.year + target_index // 12
    target_month = target_index % 12 + 1
    target_day = min(source_date.day, calendar.monthrange(target_year, target_month)[1])
    return date(target_year, target_month, target_day)


def warning_date(item):
    months = item.warning_months or DEFAULT_WARNING_MONTHS
    return add_calendar_months(item.date_added, months)


def is_old_item(item, today=None):
    today = today or date.today()
    return today >= warning_date(item)
