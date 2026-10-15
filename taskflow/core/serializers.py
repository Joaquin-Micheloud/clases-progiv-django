from datetime import date 
from rest_framework import serializers 
from .models import Project, Task, Tag 
from .services import HolidayService

class TagSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = Tag 
        fields = ["id", "name"] 

class TaskSerializer(serializers.ModelSerializer): 
    tags = TagSerializer(many=True, read_only=True)
    due_on_holiday = serializers.SerializerMethodField()

    class Meta: 
        model = Task 
        fields = [ 
            "id", "project", "title", "description", 
            "priority", "status", "due_date","due_on_holiday", "tags", "created_at", 
        ]
    
    def get_due_on_holiday(self, obj) -> bool:
        """Determina si la fecha límite coincide con un feriado (Clase 5)."""
        if not obj.due_date:
            return False
        return HolidayService.is_holiday(obj.due_date)

    def validate_due_date(self, value): 
        if value and value < date.today(): 
            raise serializers.ValidationError("La fecha límite no puede ser en el pasado.") 
        return value 

    def validate(self, data):
        instance = self.instance

        status = data.get("status", instance.status if instance else None)[cite: 1, 7]
        due_date = data.get("due_date", instance.due_date if instance else None)[cite: 1, 7]
        project = data.get("project", instance.project if instance else None)[cite: 1, 7]

        if status == "completada" and not due_date:
         raise serializers.ValidationError(
                "No se puede marcar una tarea como completada sin fecha límite registrada."
            )[cite: 1, 7]

        if status == "en_progreso" and project:
            hay_completadas = project.tasks.filter(status="completada").exists()[cite: 1, 7]
            if not hay_completadas:
                raise serializers.ValidationError(
                    "No se puede pasar a 'en_progreso' una tarea de un proyecto "
                    "que todavía no tiene ninguna tarea completada."
                )[cite: 1, 7]

        return data[cite: 1, 7]

class ProjectSerializer(serializers.ModelSerializer): 
    tasks = TaskSerializer(many=True, read_only=True) 

    class Meta: 
        model = Project 
        fields = ["id", "name", "description", "tasks", "created_at"] 