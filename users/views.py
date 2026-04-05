import uuid

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import InvitationForm, ProfileUpdateForm, UserRegisterForm
from .models import Invitation


def _is_platform_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@require_POST
def custom_logout(request):
    logout(request)
    return redirect("login")


def register(request):
    token = request.GET.get("token") or request.POST.get("token")
    invitation = None

    if token:
        try:
            invitation = Invitation.objects.get(token=uuid.UUID(str(token)), used=False)
        except (Invitation.DoesNotExist, ValueError):
            messages.error(request, "Invalid or already-used invitation link.")
            return redirect("login")
    else:
        messages.error(request, "A valid invitation link is required to register.")
        return redirect("login")

    if request.method == "POST":
        form = UserRegisterForm(request.POST, invitation=invitation)
        if form.is_valid():
            user = form.save()

            user.profile.role = "member"
            user.profile.save()

            if invitation.project:
                from blog.models import ProjectMember

                ProjectMember.objects.get_or_create(
                    project=invitation.project,
                    user=user,
                    defaults={"role": "member"},
                )

            invitation.used = True
            invitation.save()

            messages.success(request, f"Account created for {user.username}. You can now log in.")
            return redirect("login")
    else:
        form = UserRegisterForm(invitation=invitation, initial={"email": invitation.email})

    return render(
        request,
        "users/register.html",
        {
            "form": form,
            "token": token,
            "invitation_username": invitation.username,
        },
    )


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

    memberships = (
        ProjectMember.objects.filter(user=request.user)
        .select_related("project")
        .order_by("project__name")
    )

    managed_projects = Project.objects.filter(manager=request.user).order_by("name")

    assigned_tickets = (
        Ticket.objects.filter(assignee=request.user)
        .select_related("project", "epic", "sprint")
        .order_by("status", "backlog_order", "date_posted")
    )

    created_tickets = (
        Ticket.objects.filter(author=request.user)
        .select_related("project", "epic", "sprint")
        .order_by("-date_posted")[:10]
    )

    context = {
        "p_form": p_form,
        "memberships": memberships,
        "managed_projects": managed_projects,
        "assigned_tickets": assigned_tickets,
        "created_tickets": created_tickets,
        "is_platform_admin": _is_platform_admin(request.user),
    }
    return render(request, "users/profile.html", context)


@login_required
def invite_user(request):
    if not _is_platform_admin(request.user):
        messages.error(request, "Only platform administrators can send invitations.")
        return redirect("blog-home")

    invitations = Invitation.objects.filter(created_by=request.user).order_by("-created_at")

    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.created_by = request.user
            inv.role_assigned = "member"
            inv.save()
            messages.success(request, f"Invitation created for {inv.email}.")
            return redirect("invite-user")
    else:
        form = InvitationForm()

    return render(request, "users/invite.html", {"form": form, "invitations": invitations})


@login_required
def manage_roles(request):
    if not _is_platform_admin(request.user):
        messages.error(request, "Only platform administrators can manage roles.")
        return redirect("blog-home")

    from .models import Profile

    profiles = Profile.objects.select_related("user").order_by("user__username")
    return render(request, "users/manage_roles.html", {"profiles": profiles})


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
