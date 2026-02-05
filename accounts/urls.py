from django.urls import path
from django.views.generic import RedirectView

from accounts.views.login import request_login_otp_view
from accounts.views.auth import verify_login_otp_view
from accounts.views.security import logout_view
from accounts.views.password_reset import *
from accounts.views.register import *




app_name = "accounts"

urlpatterns = [
    # Friendly login URL
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




    path(
        "password-reset/",
        RedirectView.as_view(
            pattern_name="accounts:password-reset-request",
            permanent=False,
        ),
     ),
    path(
        "password-reset/request/",
        request_password_reset_otp_view,
        name="password-reset-request",
    ),
    path(
        "password-reset/verify/",
        verify_password_reset_otp_view,
        name="password-reset-verify",
    ),

     path(
        "password-reset/success/",
        password_reset_success_view,
        name="password-reset-success",
    ),


    path("register/", register_view, name="register"),
    path(
        "register/verify/",
        verify_registration_otp_view,
        name="verify-registration-otp",
    ),
    path(
        "register/success/",
        registration_success_view,
        name="registration-success",
    ),

    
]

