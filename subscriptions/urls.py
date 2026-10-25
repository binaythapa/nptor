# subscriptions/urls.py

from django.urls import path

from .views import cancel_user_subscription, subscription_history


app_name = "subscriptions"


urlpatterns = [
    path(
        "history/",
        subscription_history,
        name="subscription_history",
    ),
    path(
        "<int:subscription_id>/cancel/",
        cancel_user_subscription,
        name="cancel_subscription",
    ),
]
