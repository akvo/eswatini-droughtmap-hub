from rest_framework.permissions import BasePermission, SAFE_METHODS

from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.constants import ActivityStatus


class CanManageActivity(BasePermission):
    """
    Read: any authenticated user (no anonymous access).
    Create: admin or reviewer (own-sector enforced in the serializer).
    Update: admin any; reviewer only own-sector drafts.
    Delete: admin only.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        action = getattr(view, "action", None)
        if action == "create":
            return user.role in (UserRoleTypes.admin, UserRoleTypes.reviewer)
        return True  # object-level check below decides update/destroy

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return True
        if user.role == UserRoleTypes.admin:
            return True
        # Reviewer acting as sector lead: own-sector drafts, edits only.
        if (user.role == UserRoleTypes.reviewer
                and user.activity_sector == obj.sector
                and obj.status == ActivityStatus.draft
                and request.method in ("PUT", "PATCH")):
            return True
        return False
