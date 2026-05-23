from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Only users with role=admin can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsManagerOrAdmin(BasePermission):
    """Only managers and admins can access."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['admin', 'manager']
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level: only the owner or admin can edit."""
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return obj == request.user or getattr(obj, 'owner', None) == request.user