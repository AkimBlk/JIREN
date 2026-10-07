from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, View

from ..forms import NON_ADMIN_PROJECT_ROLE_CHOICES, ProjectMemberForm, ProjectMemberRoleForm
from ..models import Project, ProjectMember
from .permissions import is_admin, require_project_admin


class ProjectAdminRequiredMixin(LoginRequiredMixin):
    project = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.project = self._load_project(kwargs.get("pk"))
        require_project_admin(request.user, self.project)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _load_project(project_id):
        if project_id is None:
            raise Http404("Project not found.")
        return get_object_or_404(Project.objects.select_related("manager"), pk=project_id)


class ProjectMemberListView(ProjectAdminRequiredMixin, DetailView):
    model = Project
    context_object_name = "project"
    template_name = "blog/project_detail.html"

    def get_queryset(self):
        return Project.objects.select_related("manager").prefetch_related("members__user")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        members = self.object.members.select_related("user").order_by("user__username")
        ctx["members"] = members
        ctx["membership_management_enabled"] = True
        ctx["member_form"] = kwargs.get("member_form") or ProjectMemberForm(project=self.object)
        ctx["member_role_choices"] = NON_ADMIN_PROJECT_ROLE_CHOICES
        ctx["project_summary"] = {"member_count": members.count()}
        ctx["user_is_admin"] = is_admin(self.request.user)
        return ctx


class ProjectMemberAddView(ProjectMemberListView):
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        member_form = ProjectMemberForm(request.POST, project=self.object)
        if member_form.is_valid():
            membership = member_form.save()
            messages.success(request, f"{membership.user.username} added to the project.")
            return redirect("project-members", pk=self.object.pk)
        messages.error(request, "Unable to add member. Please review the form.")
        return self.render_to_response(self.get_context_data(member_form=member_form))


@method_decorator(require_POST, name="dispatch")
class ProjectMemberRemoveView(ProjectAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        member = _project_member_or_404(self.project, kwargs.get("upk"))
        if member.user_id == self.project.manager_id:
            messages.error(request, "Project manager cannot be removed.")
        else:
            member.delete()
            messages.success(request, "Project member removed.")
        return redirect("project-members", pk=self.project.pk)


@method_decorator(require_POST, name="dispatch")
class ProjectMemberRoleView(ProjectAdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        member = _project_member_or_404(self.project, kwargs.get("upk"))
        if member.user_id == self.project.manager_id:
            messages.error(request, "Project manager role cannot be changed.")
            return redirect("project-members", pk=self.project.pk)
        role_form = ProjectMemberRoleForm(request.POST, member=member)
        if role_form.is_valid():
            role_form.save()
            messages.success(request, "Project member role updated.")
        else:
            messages.error(request, "Unable to update role.")
        return redirect("project-members", pk=self.project.pk)


def _project_member_or_404(project, user_id):
    return get_object_or_404(
        ProjectMember.objects.select_related("user"),
        project=project,
        user_id=user_id,
    )
