import csv
import json
import logging
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from core.models import Project, Task

logger = logging.getLogger("import_tasks")
if not logger.handlers:
    logger.setLevel(logging.WARNING)
    file_handler = logging.FileHandler("import.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

class Command(BaseCommand):
    help = "Importa tareas desde múltiples proveedores (JSON, CSV, XML)"

    def handle(self, *args, **options):
        default_project, _ = Project.objects.get_or_create(
            name="Proyecto Importado",
            defaults={"description": "Proyecto creado automáticamente para tareas importadas"}
        )

        total = 0
        total += self._import_json("data/tasks_provider_a.json", source="proveedor_a", project=default_project)
        total += self._import_csv("data/tasks_provider_b.csv", source="proveedor_b", project=default_project)
        total += self._import_xml("data/tasks_provider_c.xml", source="proveedor_c", project=default_project)
        total += self._import_json("data/tasks_provider_d.json", source="proveedor_d", project=default_project)
        self.stdout.write(
            self.style.SUCCESS(f"Importación finalizada: {total} tareas cargadas")
            )

    def _import_json(self, path, source, project):
        count = 0
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if self._crear_task(item, source, project):
                        count += 1
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.stderr.write(self.style.ERROR(f"Error importando {path}: {e}"))
            logger.error(msg)
        return count

    def _import_csv(self, path, source, project):
        count = 0
        try:
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for item in reader:
                    if self._crear_task(item, source, project):
                        count += 1
        except FileNotFoundError as e:
            self.stderr.write(self.style.ERROR(f"Error importando {path}: {e}"))
            logger.error(msg)
        return count

    def _import_xml(self, path, source, project):
        count = 0
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for task_node in root.findall("task"):
                item = {
                    "title": task_node.find("title").text if task_node.find("title") is not None else None,
                    "priority": task_node.find("priority").text if task_node.find("priority") is not None else "media",
                    "status": task_node.find("status").text if task_node.find("status") is not None else "pendiente",
                }
                if self._crear_task(item, source, project):
                    count += 1
        except (FileNotFoundError, ET.ParseError) as e:
            self.stderr.write(self.style.ERROR(f"Error importando {path}: {e}"))
            logger.error(msg)
        return count

    def _crear_task(self, item, source, project):
        if not item.get("title"):
            msg = f"[{source}] Item sin título omitido: {item}"
            self.stderr.write(self.style.WARNING(msg))
            logger.warning(msg)
            return False

        Task.objects.create(
            project=project,
            title=item["title"],
            priority=item.get("priority", "media"),
            status=item.get("status", "pendiente"),
        )
        return True