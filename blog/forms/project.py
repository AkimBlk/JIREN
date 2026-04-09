from django import forms
from django.contrib.auth.models import User

from ..models import Project, ProjectMember, Sprint

NON_ADMIN_PROJECT_ROLE_CHOICES = [
    (ProjectMember.ROLE_CONTRIBUTOR, "Contributor"),
    (ProjectMember.ROLE_READ_ONLY, "Read only"),
]


class ProjectForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.order_by("username"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Project
        fields = [
            "code_prefix", "name", "description",
            "start_date", "end_date", "members",
        ]
        widgets = {
            "description": forms.Textarea(attrs={
                "rows": 8,
                "class": "form-control",
            }),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None
        if self.instance.pk:
            self.fields["members"].initial = self.instance.members.values_list("user_id", flat=True)

    def clean_code_prefix(self):
        code_prefix = (self.cleaned_data.get("code_prefix") or "").strip().upper()
        return code_prefix or None

    def clean(self):
        cleaned_data = super().clean()
        self.instance.capacity_mode = Project.CAPACITY_MODE_PER_USER
        self.instance.global_capacity = None
        return cleaned_data

    def clean_description(self):
        return str(self.cleaned_data.get("description", "") or "").strip()

    def save(self, commit=True):
        project = super().save(commit=False)
        # These fields are no longer user-configurable in the form.
        project.capacity_mode = Project.CAPACITY_MODE_PER_USER
        project.global_capacity = None
        if commit:
            project.save()
            self.save_m2m()
        return project

    def sync_members(self, project, manager):
        selected_users = list(self.cleaned_data.get("members", []))
        if manager not in selected_users:
            selected_users.append(manager)
        selected_ids = {user.id for user in selected_users}
        project.members.exclude(user=manager).exclude(user_id__in=selected_ids).delete()
        for user in selected_users:
            role = ProjectMember.ROLE_ADMIN if user == manager else ProjectMember.ROLE_CONTRIBUTOR
            ProjectMember.objects.update_or_create(project=project, user=user, defaults={"role": role})


class ProjectMemberForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), empty_label=None)
    role = forms.ChoiceField(choices=NON_ADMIN_PROJECT_ROLE_CHOICES)

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields["user"].queryset = self._available_users()
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def _available_users(self):
        existing_ids = self.project.members.values_list("user_id", flat=True)
        return User.objects.exclude(pk__in=existing_ids).exclude(pk=self.project.manager_id).order_by("username")

    def clean_user(self):
        selected_user = self.cleaned_data["user"]
        if selected_user.pk == self.project.manager_id:
            raise forms.ValidationError("Project manager is already an administrator.")
        return selected_user

    def save(self):
        return ProjectMember.objects.create(
            project=self.project,
            user=self.cleaned_data["user"],
            role=self.cleaned_data["role"],
        )


class ProjectMemberRoleForm(forms.Form):
    role = forms.ChoiceField(choices=NON_ADMIN_PROJECT_ROLE_CHOICES)

    def __init__(self, *args, member, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member
        self.fields["role"].initial = member.role
        self.fields["role"].widget.attrs["class"] = "form-control"

    def save(self):
        self.member.role = self.cleaned_data["role"]
        self.member.save(update_fields=["role"])
        return self.member


class SprintAdminForm(forms.ModelForm):
    workload_unit = forms.ChoiceField(choices=Project.WORKLOAD_UNIT_CHOICES)

    class Meta:
        model = Sprint
        fields = ["name", "start_date", "end_date", "objective", "workload_unit", "capacity_mode", "capacity"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "objective": forms.Textarea(attrs={"rows": 5, "class": "form-control", "maxlength": "1000"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project and not self.is_bound:
            self.fields["workload_unit"].initial = project.workload_unit

    def save(self, commit=True):
        sprint = super().save(commit=False)
        if self.project:
            self.project.workload_unit = self.cleaned_data["workload_unit"]
            self.project.save(update_fields=["workload_unit"])
        if commit:
            sprint.save()
            self.save_m2m()
        return sprint

    def clean_objective(self):
        return str(self.cleaned_data.get("objective") or "").strip()


class SprintStatusForm(forms.Form):
    status = forms.ChoiceField(label="Status")

    ALLOWED_STATUS_CHOICES = {
        Sprint.STATUS_PLANNED: [
            (Sprint.STATUS_PLANNED, "Planned"),
            (Sprint.STATUS_ACTIVE, "Active"),
        ],
        Sprint.STATUS_ACTIVE: [
            (Sprint.STATUS_ACTIVE, "Active"),
            (Sprint.STATUS_CLOSED, "Closed"),
        ],
        Sprint.STATUS_CLOSED: [
            (Sprint.STATUS_CLOSED, "Closed"),
        ],
    }

    def __init__(self, *args, sprint=None, **kwargs):
        super().__init__(*args, **kwargs)
        if sprint is None:
            raise ValueError("SprintStatusForm requires a sprint instance.")
        self.sprint = sprint
        self.fields["status"].choices = self.ALLOWED_STATUS_CHOICES.get(sprint.status, Sprint.STATUS_CHOICES)
        self.initial.setdefault("status", sprint.status)


class RemainingLoadUpdateForm(forms.Form):
    remaining_load = forms.IntegerField(
        min_value=0,
        label="Remaining load",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
    )

    def __init__(self, *args, ticket=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ticket is None:
            raise ValueError("RemainingLoadUpdateForm requires a ticket instance.")
        self.ticket = ticket
        self.fields["remaining_load"].initial = ticket.remaining_load

    def clean_remaining_load(self):
        remaining_load = self.cleaned_data["remaining_load"]
        if remaining_load > self.ticket.initial_load:
            raise forms.ValidationError("Remaining load cannot exceed initial load.")
        return remaining_load
