from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from ..forms.git_repository import GitRepositoryForm
from ..models import GitRepository, Project
from .permissions import is_admin


class GitRepositorySetupMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin to ensure only project admins can setup Git repository.
    """

    def test_func(self):
        """Check if user is project admin."""
        project_pk = self.kwargs.get("project_pk")
        project = get_object_or_404(Project, pk=project_pk)

        # User must be project manager or superuser
        return self.request.user == project.manager or is_admin(self.request.user)

    def get_context_data(self, **kwargs):
        """Add project to context."""
        context = super().get_context_data(**kwargs)
        context["project"] = get_object_or_404(Project, pk=self.kwargs["project_pk"])
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

        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return not hasattr(project, "git_repository")

    def form_valid(self, form):
        """Save form and link to project."""
        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        form.instance.project = project

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
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
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
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

        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return hasattr(project, "git_repository")

    def get_object(self, queryset=None):
        """Get the Git repository for the project."""
        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return project.git_repository

    def form_valid(self, form):
        """Save form — keep existing token if field left empty."""
        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])

        if not form.cleaned_data.get("access_token"):
            form.instance.access_token = self.get_object().access_token

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
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
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
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
