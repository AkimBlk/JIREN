from django.contrib import admin

from .models import Project, ProjectMember, Sprint, SprintUserCapacity, StoryPointsScheme, Tag, Ticket, TicketAttachment, TicketLink


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "issue_type", "status", "priority")
    list_filter = ("project", "issue_type", "status", "priority", "tags")
    search_fields = ("title", "description")
    filter_horizontal = ("tags",)


@admin.register(TicketLink)
class TicketLinkAdmin(admin.ModelAdmin):
    list_display = ("source_ticket", "link_type", "target_ticket", "created_at")
    list_filter = ("link_type",)
    search_fields = ("source_ticket__title", "target_ticket__title")


admin.site.register(Project)
admin.site.register(ProjectMember)
admin.site.register(Sprint)
admin.site.register(SprintUserCapacity)
admin.site.register(TicketAttachment)


@admin.register(StoryPointsScheme)
class StoryPointsSchemeAdmin(admin.ModelAdmin):
    list_display = ("project", "scheme_type")
    list_filter = ("scheme_type",)
    search_fields = ("project__name",)
    readonly_fields = ("project",)
