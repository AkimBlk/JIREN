from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Invitation, Profile

USERNAME_FIELD = User._meta.get_field("username")


def _append_widget_class(widget, css_class):
    existing_class = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{existing_class} {css_class}".strip()


def _style_form_fields(fields):
    for field in fields.values():
        widget = field.widget
        input_type = getattr(widget, "input_type", "")

        if input_type == "hidden":
            continue

        if input_type in {"checkbox", "radio"}:
            _append_widget_class(widget, "form-check-input")
            continue

        _append_widget_class(widget, "form-control")


def _clear_help_texts(fields):
    for field in fields.values():
        field.help_text = None


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self.fields)
        _clear_help_texts(self.fields)
        self.fields["username"].label = "Username"
        self.fields["username"].widget.attrs.update(
            {
                "placeholder": "Username",
                "autocomplete": "username",
            }
        )
        self.fields["password"].label = "Password"
        self.fields["password"].widget.attrs.update(
            {
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        )


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self.fields)
        _clear_help_texts(self.fields)
        self.fields["old_password"].label = "Current password"
        self.fields["old_password"].widget.attrs.update(
            {
                "placeholder": "Current password",
                "autocomplete": "current-password",
            }
        )
        self.fields["new_password1"].label = "New password"
        self.fields["new_password1"].widget.attrs.update(
            {
                "placeholder": "New password",
                "autocomplete": "new-password",
            }
        )
        self.fields["new_password2"].label = "Confirm password"
        self.fields["new_password2"].widget.attrs.update(
            {
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        )


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    def __init__(self, *args, invitation, **kwargs):
        self.invitation = invitation
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)
        self.fields["email"].initial = invitation.email
        _style_form_fields(self.fields)
        _clear_help_texts(self.fields)
        self.fields["email"].label = "Email"
        self.fields["email"].widget.attrs.update(
            {
                "placeholder": "Email",
                "autocomplete": "email",
            }
        )
        self.fields["password1"].label = "Password"
        self.fields["password1"].widget.attrs.update(
            {
                "placeholder": "Password",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].widget.attrs.update(
            {
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        )

    def clean(self):
        cleaned_data = super().clean()

        if User.objects.filter(username=self.invitation.username).exists():
            raise forms.ValidationError(
                "This invitation username is no longer available. Please contact your Super Admin."
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.invitation.username
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            self.save_m2m()

        return user

    class Meta:
        model = User
        fields = ["email", "password1", "password2"]


class ProfileUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self.fields)

    class Meta:
        model = Profile
        fields = ["image"]


class RoleUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self.fields)

    class Meta:
        model = Profile
        fields = ["role"]
        widgets = {
            "role": forms.Select(choices=Profile.ROLE_CHOICES)
        }


class InvitationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self.fields)
        _clear_help_texts(self.fields)

    class Meta:
        model = Invitation
        fields = ["email", "username", "project"]
        labels = {
            "email": "Email address",
            "username": "Username",
            "project": "Project (optional)",
        }
