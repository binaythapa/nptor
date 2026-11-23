# organizations/services/analytics/filters.py

from datetime import timedelta
from django.utils import timezone


VALID_RANGES = {
    "7d": {"label": "Last 7 Days", "days": 7},
    "30d": {"label": "Last 30 Days", "days": 30},
    "90d": {"label": "Last 90 Days", "days": 90},
    "1y": {"label": "Last 12 Months", "days": 365},
    "all": {"label": "All Time", "days": None},
}


def parse_date_range(range_param):
    """
    Parse date range parameter and return (start_datetime, end_datetime, active_range, range_label).

    Supported ranges:
      - '7d'  : 7 days
      - '30d' : 30 days (default)
      - '90d' : 90 days
      - '1y'  : 365 days
      - 'all' : unbounded (start_datetime = None)
    """
    now = timezone.now()
    active_range = (range_param or "").lower().strip()
    if active_range not in VALID_RANGES:
        active_range = "30d"

    range_info = VALID_RANGES[active_range]
    days = range_info["days"]

    if days is not None:
        start_datetime = now - timedelta(days=days)
    else:
        start_datetime = None

    return start_datetime, now, active_range, range_info["label"]
