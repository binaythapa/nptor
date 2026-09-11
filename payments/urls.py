from django.urls import path

from payments.views import (
    course_checkout,
    track_checkout,
    subscription_plans,
    subscription_checkout,
    payment_checkout,
    payment_verify,
    payment_success,
)

app_name = "payments"

urlpatterns = [
    path("subscriptions/", subscription_plans, name="subscription_plans"),
    path("course/<int:course_id>/checkout/", course_checkout, name="course_checkout"),
    path("track/<int:track_id>/checkout/", track_checkout, name="track_checkout"),
    path("subscription/<int:plan_id>/checkout/", subscription_checkout, name="subscription_checkout"),
    path("checkout/<str:order_number>/", payment_checkout, name="payment_checkout"),
    path("checkout/<str:order_number>/verify/", payment_verify, name="payment_verify"),
    path("checkout/<str:order_number>/success/", payment_success, name="payment_success"),
]
