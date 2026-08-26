import hmac
from django.conf import settings
from rest_framework.permissions import BasePermission
from api.v1.v1_users.constants import UserRoleTypes


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == UserRoleTypes.reviewer:
            return True
        return False


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == UserRoleTypes.admin:
            return True
        return False


class IsObserver(BasePermission):
    """Citizen-science observer: must have the role AND a bound Inkhundla —
    every observer endpoint scopes by request.user.administration."""

    def has_permission(self, request, view):
        return (
            request.user.role == UserRoleTypes.observer
            and request.user.administration_id is not None
        )


class HasApiKey(BasePermission):
    """Authenticates machine-to-machine pipeline push endpoints.

    Reads the raw key from the request META header defined by
    X_API_KEY_HEADER (default: HTTP_X_API_KEY) and compares it to
    settings.X_API_KEY using a constant-time comparison (D-4).
    No SystemUser / JWT involved — these endpoints are key-only.
    """

    def has_permission(self, request, view):
        sent = request.META.get(settings.X_API_KEY_HEADER, "")
        if not sent:
            return False
        return hmac.compare_digest(sent, settings.X_API_KEY)
