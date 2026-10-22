from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError, AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Project, ProjectMembership, SecurityLog
from .permissions import IsProjectAdminOrReadOnly
from .repositories import TaskRepository
from .serializers import ProjectSerializer, TaskSerializer
from .serializers_auth import RegisterSerializer
from .services import MembershipService, TaskService

import logging
from rest_framework_simplejwt.views import TokenObtainPairView
from .throttles import LoginRateThrottle

def health_check(request):
    return JsonResponse({"status": "ok", "service": "TaskFlow API"})


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("id")
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectAdminOrReadOnly]

    def get_queryset(self):
        return MembershipService.projects_for(self.request.user)

    def perform_create(self, serializer):
        with transaction.atomic():
            project = serializer.save()
            ProjectMembership.objects.create(
                project=project, user=self.request.user, role="admin"
            )

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        project = self.get_object()

        username = request.data.get("username")
        role = request.data.get("role", "miembro")

        if not username:
            raise ValidationError({"username": "Este campo es requerido."})

        try:
            user_to_add = User.objects.get(username=username)
        except User.DoesNotExist:
            raise NotFound({"detail": f"El usuario '{username}' no existe."})

        if ProjectMembership.objects.filter(
            project=project, user=user_to_add
        ).exists():
            raise ValidationError(
                {"detail": f"El usuario '{username}' ya es miembro de este proyecto."}
            )

        membership = ProjectMembership.objects.create(
            project=project, user=user_to_add, role=role
        )

        return Response(
            {
                "message": f"Usuario '{username}' agregado exitosamente como '{role}'.",
                "membership_id": membership.id,
            },
            status=201,
        )


class TaskViewSet(viewsets.ModelViewSet):
    queryset = TaskRepository.get_queryset()
    serializer_class = TaskSerializer
    filterset_fields = ["status", "priority", "project"]
    ordering_fields = ["due_date", "created_at", "priority"]
    search_fields = ["title", "description"]
    permission_classes = [IsAuthenticated, IsProjectAdminOrReadOnly]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(project__memberships__user=self.request.user)
            .distinct()
        )

    def check_project_admin(self, project):
        if not MembershipService.is_admin(self.request.user, project):
            raise PermissionDenied(
                "Solo un administrador del proyecto puede realizar esta acción."
            )

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        self.check_project_admin(project)
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        project = serializer.validated_data.get(
            "project", serializer.instance.project
        )
        self.check_project_admin(project)
        serializer.save()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        TaskService.mark_completed(task)
        return Response(self.get_serializer(task).data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        tasks = TaskService.tasks_overdue(self.get_queryset())
        page = self.paginate_queryset(tasks)
        if page is not None:
            return self.get_paginated_response(
                self.get_serializer(page, many=True).data
            )
        return Response(self.get_serializer(tasks, many=True).data)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class SocialLoginJWTView(APIView):
    def get(self, request):
        refresh = RefreshToken.for_user(request.user)
        return Response(
            {"refresh": str(refresh), "access": str(refresh.access_token)}
        )

security_logger = logging.getLogger("security")

class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            ip = request.META.get("REMOTE_ADDR")
            username = request.data.get("username", "desconocido")
            SecurityLog.objects.create(
                user=None,
                ip_address=ip,
                action="login_failed",
                details=f"Intento fallido para el usuario: {username}"
            )
            security_logger.warning(f"Intento de login fallido desde IP {ip} para usuario {username}")
            raise