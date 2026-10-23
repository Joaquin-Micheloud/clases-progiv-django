from rest_framework import permissions
from .services import MembershipService
from .models import SecurityLog

class IsProjectAdminOrReadOnly(permissions.BasePermission):
    """
    Cualquier miembro del proyecto puede leer (SAFE_METHODS).
    Solo un admin del proyecto puede modificar (editar/borrar/crear).
    """
    def has_object_permission(self, request, view, obj):
        project = obj.project if hasattr(obj, "project") else obj
        
        if request.method in permissions.SAFE_METHODS:
            return MembershipService.is_member(request.user, project)
        
        is_admin = MembershipService.is_admin(request.user, project)
        
        if not is_admin and MembershipService.is_member(request.user, project):
            ip = request.META.get("REMOTE_ADDR")
            SecurityLog.objects.create(
                user=request.user,
                ip_address=ip,
                action="permission_denied",
                details=f"Intento no autorizado de {request.method} en el proyecto {project.id}"
            )
            
        return is_admin