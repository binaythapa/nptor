from django.urls import path

from payments.views import (
    course_checkout,
    track_checkout,
    exam_checkout,
    payment_checkout,
    payment_verify,
    payment_success,
)

app_name = "payments"


urlpatterns = [

    # Course
    path(
        "course/<int:course_id>/checkout/",
        course_checkout,
        name="course_checkout",
    ),

    # Track
    path(
        "track/<int:track_id>/checkout/",
        track_checkout,
        name="track_checkout",
    ),

    # Individual Exam
    path(
        "exam/<int:exam_id>/checkout/",
        exam_checkout,
        name="exam_checkout",
    ),

    # Payment checkout
    path(
        "checkout/<str:order_number>/",
        payment_checkout,
        name="payment_checkout",
    ),

    # Payment verification
    path(
        "checkout/<str:order_number>/verify/",
        payment_verify,
        name="payment_verify",
    ),

    # Payment success
    path(
        "checkout/<str:order_number>/success/",
        payment_success,
        name="payment_success",
    ),
]