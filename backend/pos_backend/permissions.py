from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners and superusers to access the endpoint.
    """
    @staticmethod
    def check_is_owner(user):
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        role = getattr(user, 'role', None)
        if role and getattr(role, 'name', '').lower() == 'owner':
            return True
        return False

    def has_permission(self, request, view):
        return self.check_is_owner(request.user)

class IsOwnerOrSelf(permissions.BasePermission):
    """
    Custom permission to allow owners, superusers, or the user themselves (e.g. for profile endpoints)
    to access the endpoint.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        role = getattr(user, 'role', None)
        if role and getattr(role, 'name', '').lower() == 'owner':
            return True
        # If the object is the user itself, allow
        if hasattr(obj, 'user') and obj.user == user:
            return True
        if obj == user:
            return True
        return False
