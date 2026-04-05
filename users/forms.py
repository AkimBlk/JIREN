from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Invitation, Profile

USERNAME_FIELD = User._meta.get_field("username")


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    def __init__(self, *args, invitation, **kwargs):
        self.invitation = invitation
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)
        self.fields["email"].initial = invitation.email

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
    class Meta:
        model = Profile
        fields = ["image"]


class RoleUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["role"]
        widgets = {
            "role": forms.Select(choices=Profile.ROLE_CHOICES)
        }

class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["email", "username", "project"]
        labels = {
            "email": "Email address",
            "username": "Username",
            "project": "Project (optional)",
        }
        help_texts = {
            "username": USERNAME_FIELD.help_text,
        }
