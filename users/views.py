from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from .forms import InvitationForm, LoginForm, ProfileUpdateForm, UserRegisterForm
from .models import Invitation, Profile


def _is_platform_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@require_POST
def custom_logout(request):
    logout(request)
    return redirect("login")


def _with_password_alias(post_data):
    mapped_data = post_data.copy()
    raw_password = (mapped_data.get("password") or mapped_data.get("password1") or "").strip()
    if raw_password:
        mapped_data["password1"] = raw_password
        mapped_data["password2"] = raw_password
    return mapped_data


class RegisterView(FormView):
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)

        token = request.GET.get("token") or request.POST.get("token")
        if not token:
            messages.error(request, "Invitation token is missing.")
            return redirect("login")

        try:
            self.invitation = Invitation.objects.get(token=token, used=False)
        except Invitation.DoesNotExist:
            messages.error(request, "This invitation is invalid or has already been used.")
            return redirect("login")

        return super().dispatch(request, *args, **kwargs)

        

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["invitation"] = self.invitation

        if self.request.method == "POST":
            kwargs["data"] = _with_password_alias(self.request.POST)

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invitation"] = self.invitation
        return context

    def form_valid(self, form):
        user = form.save()

        profile = user.profile
        profile.role = self.invitation.role_assigned
        profile.save()

        if self.invitation.project:
            from blog.models import ProjectMember
            ProjectMember.objects.get_or_create(
                project=self.invitation.project,
                user=user,
                defaults={"role": "member"},
            )

        self.invitation.used = True
        self.invitation.save(update_fields=["used"])

        messages.success(self.request, f"Account created for {user.username}. You can now log in.")
        return super().form_valid(form)


class LoginView(auth_views.LoginView):
    template_name = "users/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def register(request, *args, **kwargs):
    return RegisterView.as_view()(request, *args, **kwargs)


@login_required
def profile(request):
    from blog.models import Project, ProjectMember, Ticket
    if request.method == "POST":
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if p_form.is_valid():
            p_form.save()
            messages.success(request, "Your account has been updated.")
            return redirect("profile")
    else:
        p_form = ProfileUpdateForm(instance=request.user.profile)

    memberships = list(
        ProjectMember.objects.filter(user=request.user)
        .select_related("project")
        .order_by("project__name")
    )

    managed_projects = list(Project.objects.filter(manager=request.user).order_by("name"))

    assigned_tickets = list(
        Ticket.objects.filter(assignee=request.user)
        .select_related("project", "epic", "sprint")
        .order_by("status", "backlog_order", "date_posted")
    )

    created_tickets = list(
        Ticket.objects.filter(author=request.user)
        .select_related("project", "epic", "sprint")
        .order_by("-date_posted")[:10]
    )

    role_profiles = []
    role_summary = None
    if _is_platform_admin(request.user):
        role_profiles = list(Profile.objects.select_related("user").order_by("user__username"))
        role_summary = {
            "total": len(role_profiles),
            "admins": sum(profile.role == Profile.ROLE_ADMIN for profile in role_profiles),
            "contributors": sum(profile.role == Profile.ROLE_CONTRIBUTOR for profile in role_profiles),
        }

    context = {
        "p_form": p_form,
        "memberships": memberships,
        "managed_projects": managed_projects,
        "assigned_tickets": assigned_tickets,
        "created_tickets": created_tickets,
        "is_platform_admin": _is_platform_admin(request.user),
        "profile_summary": {
            "managed_project_count": len(managed_projects),
            "membership_count": len(memberships),
            "assigned_ticket_count": len(assigned_tickets),
            "created_ticket_count": len(created_tickets),
        },
        "role_profiles": role_profiles,
        "role_summary": role_summary,
    }
    return render(request, "users/profile.html", context)


@login_required
def invite_user(request):
    if not _is_platform_admin(request.user):
        messages.error(request, "Only platform administrators can send invitations.")
        return redirect("blog-home")

    invitations = list(Invitation.objects.filter(created_by=request.user).order_by("-created_at"))

    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.created_by = request.user
            inv.role_assigned = Invitation.ROLE_CONTRIBUTOR
            inv.save()
            messages.success(request, f"Invitation created for {inv.email}.")
            return redirect("invite-user")
    else:
        form = InvitationForm()

    return render(
        request,
        "users/invite.html",
        {
            "form": form,
            "invitations": invitations,
            "invitation_summary": {
                "total": len(invitations),
                "pending": sum(not invitation.used for invitation in invitations),
                "used": sum(invitation.used for invitation in invitations),
            },
        },
    )


@login_required
def manage_roles(request):
    if not _is_platform_admin(request.user):
        messages.error(request, "Only platform administrators can manage roles.")
        return redirect("blog-home")

    profiles = list(Profile.objects.select_related("user").order_by("user__username"))
    return render(
        request,
        "users/manage_roles.html",
        {
            "profiles": profiles,
            "role_summary": {
                "total": len(profiles),
                "admins": sum(profile.role == Profile.ROLE_ADMIN for profile in profiles),
                "contributors": sum(profile.role == Profile.ROLE_CONTRIBUTOR for profile in profiles),
            },
        },
    )


@login_required
def update_role(request, pk):
    if not _is_platform_admin(request.user):
        messages.error(request, "Only platform administrators can update roles.")
        return redirect("blog-home")

    from django.contrib.auth.models import User
    from .models import Profile
    from .forms import RoleUpdateForm

    user = User.objects.get(pk=pk)
    profile = user.profile

    if request.method == "POST":
        form = RoleUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Role updated for {user.username}.")
            return redirect("manage-roles")
    else:
        form = RoleUpdateForm(instance=profile)

    return render(request, "users/update_role.html", {"target": profile, "form": form})
