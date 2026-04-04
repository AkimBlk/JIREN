import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project_django.settings')
import django
django.setup()

from blog.models import Tag, Ticket, Project

# Find first epic
epic = Ticket.objects.filter(issue_type='EPIC').first()
project = epic.project

print(f'Project: {project.name}')
print(f'Existing tags in this project:')
for tag in project.tags.all():
    print(f'  - {tag.name} (normalized: {tag.normalized_name})')
