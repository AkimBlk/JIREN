from django import forms
from django.contrib.auth.models import User

from ..models import Project, ProjectMember, Sprint


class RichTextTextarea(forms.Textarea):
    def format_value(self, value):
        from ..rich_text import sanitize_rich_text
        formatted_value = super().format_value(value)
        if formatted_value in (None, ""):
            return ""
        return sanitize_rich_text(formatted_value)


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
            "description": RichTextTextarea(attrs={
                "rows": 8,
                "data-rich-text-source": "true",
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
        from ..rich_text import sanitize_rich_text
        return sanitize_rich_text(self.cleaned_data.get("description", ""))

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
            role = "admin" if user == manager else "member"
            ProjectMember.objects.update_or_create(project=project, user=user, defaults={"role": role})


class SprintAdminForm(forms.ModelForm):
    workload_unit = forms.ChoiceField(choices=Project.WORKLOAD_UNIT_CHOICES)

    class Meta:
        model = Sprint
        fields = ["name", "start_date", "end_date", "objective", "workload_unit", "capacity_mode", "capacity"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "objective": RichTextTextarea(attrs={
                "rows": 6,
                "data-rich-text-source": "true",
                "class": "form-control",
            }),
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
        from ..rich_text import sanitize_rich_text
        return sanitize_rich_text(self.cleaned_data.get("objective", ""))


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
