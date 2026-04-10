from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from ..forms.git_repository import GitRepositoryForm
from ..models import GitRepository, Project
from .permissions import is_project_member


class GitRepositorySetupMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin to ensure any project member can setup Git repository.
    """

    def _is_ajax(self):
        return self.request.headers.get("x-requested-with") == "XMLHttpRequest"

    def _json_error(self, message, status=400):
        return JsonResponse({"success": False, "error": message}, status=status)

    def _project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def test_func(self):
        """Check if user is a project member."""
        return is_project_member(self.request.user, self._project())

    def handle_no_permission(self):
        if self._is_ajax():
            if not self.request.user.is_authenticated:
                return self._json_error("Authentication required.", status=401)
            return self._json_error("Access denied for this project.", status=403)
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        """Add project to context."""
        context = super().get_context_data(**kwargs)
        context["project"] = self._project()
        return context


class GitRepositoryCreateView(GitRepositorySetupMixin, CreateView):
    """Create new Git repository configuration for a project."""

    model = GitRepository
    form_class = GitRepositoryForm
    template_name = "blog/git_setup_form.html"

    def test_func(self):
        """Check if project doesn't already have a Git repository."""
        if not super().test_func():
            return False

        project = self._project()
        return not hasattr(project, "git_repository")

    def dispatch(self, request, *args, **kwargs):
        if not super().test_func():
            return self.handle_no_permission()
        if hasattr(self._project(), "git_repository"):
            if self._is_ajax():
                return self._json_error(
                    "Repository already configured. Use edit instead.",
                    status=409,
                )
            return self.handle_no_permission()
        return super(UserPassesTestMixin, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Save form and link to project."""
        project = self._project()
        form.instance.project = project

        if self._is_ajax():
            super().form_valid(form)
            return JsonResponse({
                "success": True,
                "message": "Git repository configured successfully.",
                "redirect_url": str(reverse_lazy(
                    "project-detail",
                    kwargs={"pk": project.pk},
                )),
            })

        return super().form_valid(form)

    def form_invalid(self, form):
        """Return JSON errors for AJAX requests."""
        if self._is_ajax():
            errors = "; ".join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items()
            )
            return JsonResponse({"success": False, "error": errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        """Redirect to project detail after save."""
        project_pk = self.kwargs["project_pk"]
        return reverse_lazy("project-detail", kwargs={"pk": project_pk})


class GitRepositoryUpdateView(GitRepositorySetupMixin, UpdateView):
    """Update existing Git repository configuration."""

    model = GitRepository
    form_class = GitRepositoryForm
    template_name = "blog/git_setup_form.html"

    def test_func(self):
        """Check if project has a Git repository and user can edit it."""
        if not super().test_func():
            return False

        project = self._project()
        return hasattr(project, "git_repository")

    def dispatch(self, request, *args, **kwargs):
        if not super().test_func():
            return self.handle_no_permission()
        if not hasattr(self._project(), "git_repository"):
            if self._is_ajax():
                return self._json_error(
                    "No repository configured yet. Create one first.",
                    status=404,
                )
            return self.handle_no_permission()
        return super(UserPassesTestMixin, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get the Git repository for the project."""
        project = self._project()
        return project.git_repository

    def form_valid(self, form):
        """Save form — keep existing token if field left empty."""
        project = self._project()

        if not form.cleaned_data.get("access_token"):
            form.instance.access_token = self.get_object().access_token

        if self._is_ajax():
            super().form_valid(form)
            return JsonResponse({
                "success": True,
                "message": "Git repository updated successfully.",
                "redirect_url": str(reverse_lazy(
                    "project-detail",
                    kwargs={"pk": project.pk},
                )),
            })

        return super().form_valid(form)

    def form_invalid(self, form):
        """Return JSON errors for AJAX requests."""
        if self._is_ajax():
            errors = "; ".join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items()
            )
            return JsonResponse({"success": False, "error": errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        """Redirect to project detail after save."""
        project_pk = self.kwargs["project_pk"]
        return reverse_lazy("project-detail", kwargs={"pk": project_pk})
