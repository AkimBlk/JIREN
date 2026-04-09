import json

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, RequestDataTooBig
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from ..forms import RemainingLoadUpdateForm, TicketForm
from ..models import Sprint, Ticket, TicketAttachment, TicketLink
from .permissions import (
    can_contribute,
    can_create_tickets,
    can_edit_ticket,
    project_assignees,
    require_project_contributor,
    visible_projects,
)
from .queries import project_linkable_tickets, ticket_form_project_data


def _filter_by_project_from_route(queryset, route_kwargs):
    project_id = route_kwargs.get("pk")
    ticket_id = route_kwargs.get("tpk")
    if project_id and ticket_id:
        return queryset.filter(project_id=project_id)
    return queryset


UPLOAD_TOO_LARGE_ERROR_MESSAGE = "File too large. Max upload size exceeded."


class UploadSizeGuardMixin:
    upload_too_large_error_message = UPLOAD_TOO_LARGE_ERROR_MESSAGE

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except RequestDataTooBig:
            messages.error(request, self.upload_too_large_error_message)
            return redirect(request.path)


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket

    def get_queryset(self):
        queryset = (
            Ticket.objects.filter(project__in=visible_projects(self.request.user))
            .select_related("project", "sprint", "epic", "author", "assignee")
            .prefetch_related("attachments", "tags")
        )
        return _filter_by_project_from_route(queryset, self.kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_edit_ticket"] = can_edit_ticket(self.request.user, self.object)
        ctx["can_update_remaining_load"] = (
            ctx["can_edit_ticket"]
            and self.object.issue_type in [
                Ticket.ISSUE_TYPE_STORY, Ticket.ISSUE_TYPE_BUG, Ticket.ISSUE_TYPE_TASK
            ]
        )
        ctx["remaining_load_form"] = RemainingLoadUpdateForm(ticket=self.object)
        ctx["blocked_by_tickets"] = self._get_blocked_by_tickets()
        ctx["blocks_tickets"] = self._get_blocks_tickets()
        ctx["related_tickets"] = self._get_related_tickets()
        ctx["ticket_summary"] = {
            "attachment_count": self.object.attachments.count(),
            "link_count": len(ctx["blocked_by_tickets"]) + len(ctx["blocks_tickets"]) + len(ctx["related_tickets"]),
        }
        return ctx

    def _get_blocked_by_tickets(self):
        return [
            link.target_ticket
            for link in self.object.outgoing_links.filter(link_type=TicketLink.TYPE_BLOCKED_BY)
            .select_related("target_ticket")
            .order_by("target_ticket__title", "target_ticket__id")
        ]

    def _get_blocks_tickets(self):
        return [
            link.source_ticket
            for link in self.object.incoming_links.filter(link_type=TicketLink.TYPE_BLOCKED_BY)
            .select_related("source_ticket")
            .order_by("source_ticket__title", "source_ticket__id")
        ]

    def _get_related_tickets(self):
        return [
            link.other_ticket(self.object)
            for link in TicketLink.objects.filter(link_type=TicketLink.TYPE_RELATES_TO)
            .filter(Q(source_ticket=self.object) | Q(target_ticket=self.object))
            .select_related("source_ticket", "target_ticket")
            .order_by("source_ticket__title", "target_ticket__title")
        ]


class TicketCreateView(UploadSizeGuardMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "blog/ticket_form.html"

    def test_func(self):
        project_id = self._resolve_project_id()
        if not project_id:
            return can_create_tickets(self.request.user)
        project = visible_projects(self.request.user).filter(pk=project_id).first()
        return bool(project and can_contribute(self.request.user, project))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name in ("story_points", "initial_load", "remaining_load"):
            if field_name in form.fields:
                form.fields[field_name].initial = None
                form.initial[field_name] = ""
        project_id = self._resolve_project_id()
        visible = visible_projects(self.request.user)
        self._reset_form_querysets(form, visible)
        if project_id:
            self._set_form_querysets_for_project(form, visible, project_id)
        if "color" in form.fields:
            selected_issue_type = (
                form.data.get("issue_type")
                if form.is_bound
                else (form.initial.get("issue_type") or Ticket.ISSUE_TYPE_STORY)
            )
            color_attrs = {"type": "color"}
            if selected_issue_type != Ticket.ISSUE_TYPE_EPIC:
                color_attrs["disabled"] = "disabled"
                if not form.is_bound:
                    form.fields["color"].initial = None
                    form.initial["color"] = ""
            form.fields["color"].widget = forms.TextInput(attrs=color_attrs)
        form.fields.pop("status", None)
        return form

    def _reset_form_querysets(self, form, visible):
        form.fields["project"].queryset = visible
        form.fields["sprint"].queryset = Sprint.objects.none()
        form.fields["epic"].queryset = Ticket.objects.none()
        form.fields["assignee"].queryset = get_user_model().objects.none()
        form.fields["blocked_by_tickets"].queryset = Ticket.objects.none()
        form.fields["relates_to_tickets"].queryset = Ticket.objects.none()

    def _resolve_project_id(self):
        route_project_id = self.kwargs.get("pk")
        if route_project_id:
            return route_project_id
        return self.request.GET.get("project") or self.request.POST.get("project")

    def _set_form_querysets_for_project(self, form, visible, project_id):
        project = visible.filter(pk=project_id).first()
        if not project:
            return
        form.fields["project"].initial = project.pk
        form.fields["sprint"].queryset = project.sprints.exclude(status=Sprint.STATUS_CLOSED)
        form.fields["epic"].queryset = project.tickets.filter(issue_type=Ticket.ISSUE_TYPE_EPIC)
        form.fields["assignee"].queryset = project_assignees(project)
        linkable = project_linkable_tickets(project)
        form.fields["blocked_by_tickets"].queryset = linkable
        form.fields["relates_to_tickets"].queryset = linkable

    def form_valid(self, form):
        require_project_contributor(self.request.user, form.instance.project)
        form.instance.status = Ticket.STATUS_TODO
        if form.instance.issue_type != Ticket.ISSUE_TYPE_EPIC:
            form.instance.color = None
        form.instance.author = self.request.user
        response = super().form_valid(form)
        self._save_attachments()
        return response

    def _save_attachments(self):
        for uploaded in self.request.FILES.getlist("attachments"):
            attachment = TicketAttachment(ticket=self.object, file=uploaded)
            attachment.full_clean()
            attachment.save()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ticket_project_data"] = ticket_form_project_data(self.request.user)
        ctx["existing_attachments"] = []
        ctx["origin_sha"] = self.request.GET.get("origin_sha", "")
        return ctx


class TicketUpdateView(UploadSizeGuardMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Ticket
    form_class = TicketForm
    template_name = "blog/ticket_form.html"

    def get_queryset(self):
        queryset = (
            Ticket.objects.filter(project__in=visible_projects(self.request.user))
            .select_related("project")
            .prefetch_related("tags")
        )
        return _filter_by_project_from_route(queryset, self.kwargs)

    def test_func(self):
        return can_edit_ticket(self.request.user, self.get_object())

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        project = self.object.project
        form.fields.pop("project", None)
        form.fields["sprint"].queryset = project.sprints.exclude(status=Sprint.STATUS_CLOSED)
        form.fields["epic"].queryset = project.tickets.filter(
            issue_type=Ticket.ISSUE_TYPE_EPIC
        ).exclude(pk=self.object.pk)
        form.fields["assignee"].queryset = project_assignees(project)
        linkable = project_linkable_tickets(project, exclude_ticket=self.object)
        form.fields["blocked_by_tickets"].queryset = linkable
        form.fields["relates_to_tickets"].queryset = linkable
        if "color" in form.fields:
            selected_issue_type = (
                form.data.get("issue_type")
                if form.is_bound
                else (form.initial.get("issue_type") or form.instance.issue_type)
            )
            color_attrs = {"type": "color"}
            if selected_issue_type != Ticket.ISSUE_TYPE_EPIC:
                color_attrs["disabled"] = "disabled"
            form.fields["color"].widget = forms.TextInput(attrs=color_attrs)
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ticket_project_data"] = ticket_form_project_data(self.request.user)
        ctx["existing_attachments"] = self.object.attachments.all()
        return ctx

    def form_valid(self, form):
        if form.instance.issue_type != Ticket.ISSUE_TYPE_EPIC:
            form.instance.color = None
        response = super().form_valid(form)
        for uploaded in self.request.FILES.getlist("attachments"):
            attachment = TicketAttachment(ticket=self.object, file=uploaded)
            attachment.full_clean()
            attachment.save()
        return response


class TicketDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Ticket
    template_name = "blog/ticket_confirm_delete.html"
    success_url = "/"

    def get_queryset(self):
        queryset = Ticket.objects.filter(
            project__in=visible_projects(self.request.user)
        ).select_related("project")
        return _filter_by_project_from_route(queryset, self.kwargs)

    def test_func(self):
        return can_edit_ticket(self.request.user, self.get_object())

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.project.pk})


@login_required
@require_POST
def delete_ticket_attachment(request, pk):
    attachment = get_object_or_404(
        TicketAttachment.objects.select_related("ticket__project"), pk=pk
    )
    if not can_edit_ticket(request.user, attachment.ticket):
        messages.error(request, "Access denied.")
        return redirect("blog-home")
    ticket = attachment.ticket
    attachment.file.delete(save=False)
    attachment.delete()
    messages.success(request, "Attachment deleted.")
    return redirect("ticket-update", pk=ticket.pk)


@login_required
@require_POST
def link_commit_to_ticket(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("project"), pk=pk)
    if not visible_projects(request.user).filter(pk=ticket.project_id).exists():
        return JsonResponse({"ok": False, "error": "Access denied."}, status=403)
    try:
        require_project_contributor(request.user, ticket.project)
    except PermissionDenied:
        return JsonResponse({"ok": False, "error": "Contributor role required."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        payload = {}

    sha = str(payload.get("sha") or request.POST.get("sha") or "").strip()[:40]
    message = str(payload.get("message") or request.POST.get("message") or "").strip()[:255]
    commit_url = str(payload.get("url") or request.POST.get("url") or "").strip()[:500]
    if not sha:
        return JsonResponse({"ok": False, "error": "Missing commit SHA."}, status=400)

    ticket.linked_commit_sha = sha
    ticket.linked_commit_message = message
    ticket.linked_commit_url = commit_url
    ticket.save(update_fields=["linked_commit_sha", "linked_commit_message", "linked_commit_url"])
    return JsonResponse({"ok": True})
