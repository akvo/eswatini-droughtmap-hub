from django.urls import re_path

from api.v1.v1_users.views import (
    login,
    verify_email,
    resend_verification_email,
    forgot_password,
    verify_password_code,
    reset_password,
    observer_request_link,
    observer_verify_link,
    ProfileView,
    ReviewerListAPI,
    ReviewerTreeAPI,
)

urlpatterns = [
    re_path(r"^(?P<version>(v1))/auth/login", login),
    re_path(
        r"^(?P<version>(v1))/auth/observer/request-link",
        observer_request_link,
        name="observer-request-link",
    ),
    re_path(
        r"^(?P<version>(v1))/auth/observer/verify-link",
        observer_verify_link,
        name="observer-verify-link",
    ),
    re_path(r"^(?P<version>(v1))/email/verify", verify_email),
    re_path(
        r"^(?P<version>(v1))/email/resend-verify", resend_verification_email
    ),
    re_path(r"^(?P<version>(v1))/users/me", ProfileView.as_view()),
    re_path(r"^(?P<version>(v1))/auth/forgot-password", forgot_password),
    re_path(
        r"^(?P<version>(v1))/auth/verify-password-code", verify_password_code
    ),
    re_path(r"^(?P<version>(v1))/auth/reset-password", reset_password),
    re_path(
        r"^(?P<version>(v1))/admin/reviewers-tree",
        ReviewerTreeAPI.as_view(),
        name="reviewer-tree",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/reviewers",
        ReviewerListAPI.as_view(),
        name="reviewer-list",
    ),
]
