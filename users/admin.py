from django.contrib import admin
from .models import Profile, Invitation

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_editable = ('role',)
    list_filter = ('role',)

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'created_by', 'project', 'used', 'created_at')
    list_filter = ('used',)
