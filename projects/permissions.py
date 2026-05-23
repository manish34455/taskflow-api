from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsManagerOrAdmin(BasePermission):
    """
    Only managers and admins can write (POST, PUT, DELETE).
    Anyone logged in can read (GET).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS') — read only
        if request.method in SAFE_METHODS:
            return True
        # write operations need manager or admin role
        return request.user.role in ['admin', 'manager']


class IsProjectMember(BasePermission):
    """
    Object-level permission.
    User must be the owner OR a member of the project.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        # obj is the Project instance
        return (
            obj.owner == request.user or
            request.user in obj.members.all()
        )


class IsAssignedDeveloperOrManager(BasePermission):
    """
    For tasks: developer can only update tasks assigned to them.
    Managers and admins can update any task.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['admin', 'manager']:
            return True
        # obj is the Task instance
        return obj.assigned_to == request.user