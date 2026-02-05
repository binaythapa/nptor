from django.urls import path
from django.views.generic import RedirectView

from accounts.views.login import request_login_otp_view
from accounts.views.auth import verify_login_otp_view
from accounts.views.security import logout_view

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        RedirectView.as_view(
            pattern_name="accounts:request-login-otp",
            permanent=False,
        ),
    ),
    path("login/otp/request/", request_login_otp_view, name="request-login-otp"),
    path("login/otp/verify/", verify_login_otp_view, name="verify-login-otp"),
    path("logout/", logout_view, name="logout"),
]
