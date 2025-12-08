# quiz/context_processors.py
from .models import Notification

def unread_notifications_count(request):
    if not request.user.is_authenticated:
        return {'unread_count': 0}
    qs = Notification.objects.order_by('-created_at')
    # Visible = broadcast OR in ManyToMany users
    visible = [n for n in qs if (not n.users.exists()) or (request.user in n.users.all())]
    count = sum(1 for n in visible if n.unread_for(request.user))
    return {'unread_count': count}
