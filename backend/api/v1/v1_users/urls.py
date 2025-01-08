from django.urls import re_path

from api.v1.v1_users.views import (
    login,
    verify_email,
    resend_verification_email,
    ProfileView,
)

urlpatterns = [
    re_path(r"^(?P<version>(v1))/auth/login", login),
    re_path(r"^(?P<version>(v1))/email/verify", verify_email),
    re_path(
        r"^(?P<version>(v1))/email/resend-verify",
        resend_verification_email
    ),
    re_path(r"^(?P<version>(v1))/users/me", ProfileView.as_view()),
]
