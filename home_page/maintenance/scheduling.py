import calendar
from datetime import date, timedelta


VALID_RECURRENCE_UNITS = ('once', 'day', 'week', 'month', 'year')


def _date_in_month(year, month, preferred_day):
    """Return preferred_day, or the final valid day for a shorter month."""
    final_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(preferred_day, final_day))


def next_scheduled_date(current_due, interval, unit, anchor_date):
    """Return the next date on a schedule anchored to its first due date."""
    if unit == 'day':
        return current_due + timedelta(days=interval)
    if unit == 'week':
        return current_due + timedelta(weeks=interval)
    if unit == 'month':
        elapsed_months = (
            (current_due.year - anchor_date.year) * 12
            + current_due.month
            - anchor_date.month
        )
        target_index = anchor_date.month - 1 + elapsed_months + interval
        target_year = anchor_date.year + target_index // 12
        target_month = target_index % 12 + 1
        return _date_in_month(target_year, target_month, anchor_date.day)
    if unit == 'year':
        target_year = current_due.year + interval
        return _date_in_month(target_year, anchor_date.month, anchor_date.day)
    raise ValueError(f'Unsupported recurrence unit: {unit}')


def next_future_due(current_due, interval, unit, anchor_date, today=None):
    """Advance at least once, skipping missed occurrences until after today."""
    if unit == 'once':
        return None
    if interval < 1:
        raise ValueError('Recurrence interval must be at least 1')

    today = today or date.today()
    candidate = next_scheduled_date(current_due, interval, unit, anchor_date)
    while candidate <= today:
        candidate = next_scheduled_date(candidate, interval, unit, anchor_date)
    return candidate
