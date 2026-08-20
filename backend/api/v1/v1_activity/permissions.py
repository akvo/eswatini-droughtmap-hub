from rest_framework.permissions import BasePermission, SAFE_METHODS

from api.v1.v1_users.constants import UserRoleTypes


class CanManageActivity(BasePermission):
    """
    Read: any authenticated user (no anonymous access).
    Write (create/update/delete): admin only — every other role gets the
    Activity Library read-only.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role == UserRoleTypes.admin

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == UserRoleTypes.admin
