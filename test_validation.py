#!/usr/bin/env python
"""Test story points validation in forms"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project_django.settings')

import django
django.setup()

from django.contrib.auth.models import User
from blog.models import Project, StoryPointsScheme, Ticket
from blog.forms import TicketForm

print("=" * 60)
print("STORY POINTS VALIDATION TEST")
print("=" * 60)

# Create test project with Fibonacci scheme
user = User.objects.create_user("testuser", password="test123")
project = Project.objects.create(name="Test - Story Points", code_prefix="TSP", manager=user)
scheme = StoryPointsScheme.objects.create(project=project, scheme_type="fibonacci")

print(f"\n✓ Project created: {project.name}")
print(f"✓ Scheme: {scheme.scheme_type}")
print(f"✓ Allowed values: {scheme.get_allowed_values()}")

# Test 1: Valid story point (5 is in Fibonacci)
print("\n--- TEST 1: Valid value (5) ---")
data = {
    "issue_type": "STORY",
    "title": "Test ticket",
    "project": project.id,
    "story_points": 5,
    "tags_input": "",
}
form = TicketForm(data=data)
if form.is_valid():
    print("✓ PASS: Valid story point accepted")
else:
    print(f"✗ FAIL: {form.errors}")

# Test 2: Invalid story point (7 is NOT in Fibonacci)
print("\n--- TEST 2: Invalid value (7) ---")
data["story_points"] = 7
form = TicketForm(data=data)
if not form.is_valid() and "story_points" in form.errors:
    print(f"✓ PASS: Invalid value rejected")
    print(f"  Error: {form.errors['story_points'][0]}")
else:
    print("✗ FAIL: Should have rejected value 7")

# Test 3: Switch to Linear scheme (allows 1-10)
print("\n--- TEST 3: Switch to Linear scheme ---")
scheme.scheme_type = "linear"
scheme.save()
print(f"✓ Scheme updated: {scheme.scheme_type}")
print(f"✓ Allowed values: {scheme.get_allowed_values()}")

data["story_points"] = 7
form = TicketForm(data=data)
if form.is_valid():
    print("✓ PASS: Now 7 is valid in Linear scheme")
else:
    print(f"✗ FAIL: {form.errors}")

# Test 4: Still invalid (11 > 10 in Linear)
print("\n--- TEST 4: Invalid value in Linear (11) ---")
data["story_points"] = 11
form = TicketForm(data=data)
if not form.is_valid():
    print(f"✓ PASS: Value 11 rejected in Linear scheme")
    print(f"  Error: {form.errors['story_points'][0]}")
else:
    print("✗ FAIL: Should have rejected value 11")

print("\n" + "=" * 60)
print("✓ ALL TESTS COMPLETED")
print("=" * 60)

# Cleanup
project.delete()
