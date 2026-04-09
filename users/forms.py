from django import forms
from django.contrib.auth import authenticate
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


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=150)
    last_name = forms.CharField(required=True, max_length=150)

    class Meta:
        model = User
        fields = ["email", "last_name", "first_name", "username", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self.fields)
        _clear_help_texts(self.fields)
        self.fields["email"].widget.attrs.update({"placeholder": "Email", "autocomplete": "email"})
        self.fields["last_name"].widget.attrs.update({"placeholder": "Last name", "autocomplete": "family-name"})
        self.fields["first_name"].widget.attrs.update({"placeholder": "First name", "autocomplete": "given-name"})
        self.fields["username"].widget.attrs.update({"placeholder": "Username", "autocomplete": "username"})
        self.fields["password1"].widget = forms.HiddenInput()
        self.fields["password2"].widget = forms.HiddenInput()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(StyledAuthenticationForm):
    email = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)
        self.fields["email"].label = "Email or username"
        self.fields["email"].widget.attrs.update(
            {"placeholder": "Email or username", "autocomplete": "username"}
        )

    def clean(self):
        login_identifier = (self.cleaned_data.get("email") or "").strip()
        password = self.cleaned_data.get("password")
        if not (login_identifier and password):
            raise self.get_invalid_login_error()
        username = self._resolve_username(login_identifier)
        self.user_cache = authenticate(self.request, username=username, password=password)
        if self.user_cache is None:
            raise self.get_invalid_login_error()
        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def _resolve_username(self, login_identifier):
        if "@" not in login_identifier:
            return login_identifier
        try:
            return User.objects.get(email__iexact=login_identifier).username
        except (User.DoesNotExist, User.MultipleObjectsReturned) as error:
            raise self.get_invalid_login_error() from error


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
