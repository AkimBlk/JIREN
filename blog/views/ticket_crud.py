from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from ..forms import RemainingLoadUpdateForm, TicketForm
from ..models import Sprint, Ticket, TicketAttachment, TicketLink
from ..services.git_service import GitService
from .permissions import can_edit_ticket, project_assignees, visible_projects
from .queries import project_linkable_tickets, ticket_form_project_data


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket

    def get_queryset(self):
        return (
            Ticket.objects.filter(project__in=visible_projects(self.request.user))
            .select_related("project", "sprint", "epic", "author", "assignee")
            .prefetch_related("attachments", "tags")
        )

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


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "blog/ticket_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        project_id = self.request.GET.get("project") or self.request.POST.get("project")
        visible = visible_projects(self.request.user)
        self._reset_form_querysets(form, visible)
        if project_id:
            self._set_form_querysets_for_project(form, visible, project_id)
        if "color" in form.fields:
            form.fields["color"].widget = forms.TextInput(attrs={"type": "color"})
        form.fields.pop("status", None)
        return form

    def _reset_form_querysets(self, form, visible):
        form.fields["project"].queryset = visible
        form.fields["sprint"].queryset = Sprint.objects.none()
        form.fields["epic"].queryset = Ticket.objects.none()
        form.fields["assignee"].queryset = get_user_model().objects.none()
        form.fields["blocked_by_tickets"].queryset = Ticket.objects.none()
        form.fields["relates_to_tickets"].queryset = Ticket.objects.none()

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
        ctx["recent_commits"] = self._get_recent_commits_for_project()
        return ctx

    def _get_recent_commits_for_project(self) -> list:
        """Return up to 10 recent commits for the pre-selected project (if it has a linked git repo)."""
        project_id = self.request.GET.get("project") or self.request.POST.get("project")
        if not project_id:
            return []
        try:
            project = visible_projects(self.request.user).get(pk=project_id)
            git_service = GitService(project.git_repository)
            return git_service.get_recent_commits(limit=10)
        except Exception:
            return []


class TicketUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Ticket
    form_class = TicketForm
    template_name = "blog/ticket_form.html"

    def get_queryset(self):
        return (
            Ticket.objects.filter(project__in=visible_projects(self.request.user))
            .select_related("project")
            .prefetch_related("tags")
        )

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
            form.fields["color"].widget = forms.TextInput(attrs={"type": "color"})
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
        return Ticket.objects.filter(
            project__in=visible_projects(self.request.user)
        ).select_related("project")

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
