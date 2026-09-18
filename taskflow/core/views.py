from django.http import JsonResponse 
from rest_framework.decorators import api_view 
from rest_framework.response import Response 
from .models import Project, Task 
from .serializers import ProjectSerializer, TaskSerializer 
from django.shortcuts import get_object_or_404
from rest_framework import viewsets  

def health_check(request): 
    return JsonResponse({"status": "ok", "service": "TaskFlow API"}) 

class ProjectViewSet(viewsets.ModelViewSet): 
    queryset = Project.objects.all() 
    serializer_class = ProjectSerializer 

class TaskViewSet(viewsets.ModelViewSet): 
    queryset = Task.objects.select_related("project").prefetch_related("tags").all() 
    serializer_class = TaskSerializer 

 