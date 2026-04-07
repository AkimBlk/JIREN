import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Project, Tag, Ticket
from .permissions import is_project_member, visible_projects


@login_required
def project_tags(request, pk):
    project = get_object_or_404(visible_projects(request.user), pk=pk)
    if not is_project_member(request.user, project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")
    context = {"project": project, "title": f"{project.name} - Tags Management"}
    return render(request, "blog/project_tags.html", context)


@login_required
def api_project_tags(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not is_project_member(request.user, project):
        return JsonResponse({"error": "Access denied"}, status=403)

    tags = [
        {"id": t["id"], "name": t["name"], "normalized_name": t["name"].lower().replace(" ", "-")}
        for t in project.tags.all().values("id", "name").order_by("name")
    ]
    return JsonResponse(tags, safe=False)


@login_required
@require_POST
def api_ticket_add_tag(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not is_project_member(request.user, ticket.project):
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    tag_name = data.get("tag_name", "").strip()
    if not tag_name:
        return JsonResponse({"error": "Tag name is required"}, status=400)

    tag, _ = Tag.objects.get_or_create(name=tag_name, project=ticket.project)
    ticket.tags.add(tag)

    tags = [{"id": t["id"], "name": t["name"]} for t in ticket.tags.values("id", "name").order_by("name")]
    return JsonResponse({"detail": f'Tag "{tag_name}" added', "tags": tags})


@login_required
@require_POST
def api_ticket_remove_tag(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not is_project_member(request.user, ticket.project):
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    tag_id = data.get("tag_id")
    if not tag_id:
        return JsonResponse({"error": "Tag ID is required"}, status=400)

    ticket.tags.remove(tag_id)
    tags = [{"id": t["id"], "name": t["name"]} for t in ticket.tags.values("id", "name").order_by("name")]
    return JsonResponse({"detail": "Tag removed", "tags": tags})
