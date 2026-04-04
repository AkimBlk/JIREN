import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..forms import RemainingLoadUpdateForm
from ..models import Ticket
from .permissions import can_edit_ticket, is_admin, visible_projects

ALLOWED_TRANSITIONS = {
    "TODO": ["IN_PROGRESS"],
    "IN_PROGRESS": ["TODO", "DONE"],
    "DONE": ["IN_PROGRESS"],
}


@login_required
@require_POST
def update_ticket_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if not is_admin(request.user):
        visible = visible_projects(request.user).values_list("id", flat=True)
        if ticket.project_id not in visible:
            return JsonResponse({"error": "Access denied."}, status=403)

    try:
        data = json.loads(request.body)
        new_status = data.get("status")
    except (ValueError, KeyError):
        return JsonResponse({"error": "Invalid payload."}, status=400)

    valid_statuses = [s[0] for s in Ticket.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({"error": f"Unknown status: {new_status}"}, status=400)

    allowed_next = ALLOWED_TRANSITIONS.get(ticket.status, [])
    if new_status not in allowed_next:
        return JsonResponse(
            {"error": f"Transition {ticket.status} -> {new_status} not allowed.", "allowed": allowed_next},
            status=400,
        )

    ticket.status = new_status
    ticket.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": ticket.status})


@login_required
@require_POST
def update_ticket_remaining_load(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.filter(project__in=visible_projects(request.user)).select_related("project"),
        pk=pk,
    )

    if not can_edit_ticket(request.user, ticket):
        messages.error(request, "You are not allowed to update this ticket.")
        return redirect("ticket-detail", pk=ticket.pk)

    load_types = [Ticket.ISSUE_TYPE_STORY, Ticket.ISSUE_TYPE_BUG, Ticket.ISSUE_TYPE_TASK]
    if ticket.issue_type not in load_types:
        messages.error(request, "This ticket type does not support load tracking.")
        return redirect("ticket-detail", pk=ticket.pk)

    form = RemainingLoadUpdateForm(request.POST, ticket=ticket)
    if form.is_valid():
        ticket.remaining_load = form.cleaned_data["remaining_load"]
        try:
            ticket.full_clean()
            ticket.save()
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Remaining load updated successfully.")
    else:
        messages.error(request, "; ".join(form.errors.get("remaining_load", ["Invalid remaining load."])))

    return redirect("ticket-detail", pk=ticket.pk)


