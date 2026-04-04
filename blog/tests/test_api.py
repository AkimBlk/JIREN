import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project_django.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from blog.models import Ticket, Project

# Get root user
user = User.objects.get(username='root')
client = Client()
client.force_login(user)

# Find an epic
epic = Ticket.objects.filter(issue_type='EPIC').first()
project = epic.project if epic else None

print(f'✓ User: {user.username} (superuser: {user.is_superuser})')
print(f'✓ Found epic: {epic.title if epic else "None"}')
print(f'✓ Epic ID: {epic.id if epic else "None"}')
print(f'✓ Epic project: {project.name if project else "None"}')
print()

# Test the API
if epic:
    print('=== TEST API /api/tickets/{id}/tags/add/ ===')
    response = client.post(
        f'/api/tickets/{epic.id}/tags/add/',
        data=json.dumps({'tag_name': 'test-tag'}),
        content_type='application/json'
    )
    print(f'Status: {response.status_code}')
    print(f'Response: {response.json()}')
