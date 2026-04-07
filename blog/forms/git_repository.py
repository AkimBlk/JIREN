from django import forms

from ..models import GitRepository


class GitRepositoryForm(forms.ModelForm):
    """Form for adding/editing Git repository configuration."""

    repository_url = forms.URLField(
        required=True,
        label="Repository URL",
        widget=forms.URLInput(attrs={
            "class": "form-control",
            "placeholder": "Repository URL",
        }),
    )

    repository_type = forms.ChoiceField(
        required=True,
        label="Git Provider",
        choices=GitRepository.REPOSITORY_TYPE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    access_token = forms.CharField(
        required=False,
        label="Access token",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Access token",
        }),
    )

    is_private = forms.BooleanField(
        required=False,
        label="Private repository",
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None

    class Meta:
        model = GitRepository
        fields = ["repository_url", "repository_type", "access_token", "is_private"]

    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        is_private = cleaned_data.get("is_private")
        access_token = cleaned_data.get("access_token")

        existing_token = getattr(self.instance, "access_token", None)
        has_token = bool(access_token) or bool(existing_token)

        if is_private and not has_token:
            raise forms.ValidationError(
                "Access token is required for private repositories."
            )

        return cleaned_data
