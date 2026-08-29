# subscriptions/urls.py

from django.urls import path

from .views import subscription_history


app_name = "subscriptions"


urlpatterns = [
    path(
        "history/",
        subscription_history,
        name="subscription_history",
    ),
]