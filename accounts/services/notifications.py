"""Shared notification service used by account and organization workflows.

The project currently stores notifications in the quiz app.  This service keeps
account/organization code independent from that storage location while exposing
the richer notification-call signature used by newer workflows.
"""

from quiz.models import Notification


def create_notification(
    user,
    category,
    title,
    message,
    *,
    priority="info",
    target_url=None,
    dedupe_key=None,
):
    """Create a user-targeted in-app notification.

    ``priority``, ``target_url`` and ``dedupe_key`` are accepted for the shared
    service contract.  The current ``Notification`` model does not yet persist
    those metadata fields, so they are intentionally not written to the model.
    ``dedupe_key`` is also not needed by the current access-request workflow,
    which is idempotent at the request lifecycle level.
    """
    del category, priority, target_url, dedupe_key

    if user is None:
        return None

    notification = Notification.objects.create(
        title=title,
        message=message,
    )
    notification.users.add(user)
    return notification
