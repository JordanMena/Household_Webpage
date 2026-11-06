import calendar
from datetime import date, timedelta


VALID_RECURRENCE_UNITS = ('once', 'day', 'week', 'month', 'year')


def _date_in_month(year, month, preferred_day):
    """Return preferred_day, or the final valid day for a shorter month."""
    final_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(preferred_day, final_day))


def next_due_date(completed_date, interval, unit):
    """Return one recurrence interval after completion, even if still overdue."""
    if unit == 'once':
        return None
    if interval < 1:
        raise ValueError('Recurrence interval must be at least 1')

    if unit == 'day':
        return completed_date + timedelta(days=interval)
    if unit == 'week':
        return completed_date + timedelta(weeks=interval)
    if unit == 'month':
        target_index = completed_date.month - 1 + interval
        target_year = completed_date.year + target_index // 12
        target_month = target_index % 12 + 1
        return _date_in_month(target_year, target_month, completed_date.day)
    if unit == 'year':
        return _date_in_month(
            completed_date.year + interval, completed_date.month, completed_date.day
        )
    raise ValueError(f'Unsupported recurrence unit: {unit}')
