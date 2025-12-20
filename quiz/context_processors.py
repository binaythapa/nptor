# quiz/context_processors.py
from .models import Notification



# quiz/context_processors.py
from django.db.models import Count

def unread_notifications_count(request):
    """
    SAFE context processor:
    - No reverse()
    - No translation calls
    - No circular imports
    """

    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}

    try:
        count = (
            request.user.notifications
            .filter(is_read=False)
            .count()
        )
    except Exception:
        count = 0

    return {
        "unread_notifications_count": count
    }
