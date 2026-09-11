from django.urls import path
from django.views.generic import RedirectView

from accounts.views.login import request_login_otp_view
from accounts.views.auth import verify_login_otp_view
from accounts.views.security import logout_view
from accounts.views.password_reset import request_password_reset_otp_view, verify_password_reset_otp_view, password_reset_success_view
from accounts.views.register import register_view, verify_registration_otp_view, registration_success_view, check_email_availability
from accounts.views.platform_users import user_monitoring
from accounts.views.notifications import notification_list, notification_read
from accounts.views.organization_requests import organization_requests, organization_request_detail, organization_request_approve, organization_request_reject

app_name = "accounts"

urlpatterns = [
    path("login/", RedirectView.as_view(pattern_name="accounts:request-login-otp", permanent=False)),
    path("login/otp/request/", request_login_otp_view, name="request-login-otp"),
    path("login/otp/verify/", verify_login_otp_view, name="verify-login-otp"),
    path("logout/", logout_view, name="logout"),
    path("check-email/", check_email_availability, name="check_email"),
    path("password-reset/", RedirectView.as_view(pattern_name="accounts:password-reset-request", permanent=False)),
    path("password-reset/request/", request_password_reset_otp_view, name="password-reset-request"),
    path("password-reset/verify/", verify_password_reset_otp_view, name="password-reset-verify"),
    path("password-reset/success/", password_reset_success_view, name="password-reset-success"),
    path("register/", register_view, name="register"),
    path("register/verify/", verify_registration_otp_view, name="verify-registration-otp"),
    path("register/success/", registration_success_view, name="registration-success"),
    path("admin/users/", user_monitoring, name="user_monitoring"),
    path("admin/organization-requests/", organization_requests, name="organization_requests"),
    path("admin/organization-requests/<int:pk>/", organization_request_detail, name="organization_request_detail"),
    path("admin/organization-requests/<int:pk>/approve/", organization_request_approve, name="organization_request_approve"),
    path("admin/organization-requests/<int:pk>/reject/", organization_request_reject, name="organization_request_reject"),
    path("notifications/", notification_list, name="notifications"),
    path("notifications/<int:pk>/read/", notification_read, name="notification_read"),
]
