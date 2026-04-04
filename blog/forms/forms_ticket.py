import re

from django import forms
from django.db.models import Q

from .project import RichTextTextarea
from models import Tag, Ticket, TicketLink
from models.tag import normalize_tag_name
from rich_text import sanitize_rich_text


class TicketForm(forms.ModelForm):
    tags_input = forms.CharField(
        label="Tags",
        required=False,
        help_text="Enter comma-separated tags. Existing tags are reused automatically.",
    )
    blocked_by_tickets = forms.ModelMultipleChoiceField(
        queryset=Ticket.objects.none(),
        required=False,
        label="Blocked by",
        help_text="Tickets that must be completed before this one.",
        widget=forms.SelectMultiple(attrs={"class": "form-control", "size": 6}),
    )
    relates_to_tickets = forms.ModelMultipleChoiceField(
        queryset=Ticket.objects.none(),
        required=False,
        label="Relates to",
        help_text="Related tickets shown from both sides.",
        widget=forms.SelectMultiple(attrs={"class": "form-control", "size": 6}),
    )

    class Meta:
        model = Ticket
        fields = [
            "issue_type", "title", "description", "project", "sprint", "epic",
            "assignee", "status", "priority", "tags_input", "blocked_by_tickets",
            "relates_to_tickets", "story_points", "initial_load", "remaining_load", "color",
        ]
        widgets = {
            "description": RichTextTextarea(attrs={"rows": 10, "data-rich-text-source": "true"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["blocked_by_tickets"].label_from_instance = self._ticket_label
        self.fields["relates_to_tickets"].label_from_instance = self._ticket_label

        if self.instance.pk:
            self._init_tags_field()
            self._init_link_fields()
            self.fields["initial_load"].disabled = True
            self.fields["initial_load"].help_text = "Initial load can only be set when the ticket is created."

    def _init_tags_field(self):
        self.fields["tags_input"].initial = ", ".join(
            self.instance.tags.order_by("name").values_list("name", flat=True)
        )

    def _init_link_fields(self):
        self.fields["blocked_by_tickets"].initial = self.instance.outgoing_links.filter(
            link_type=TicketLink.TYPE_BLOCKED_BY
        ).values_list("target_ticket_id", flat=True)

        raw_relates = (
            TicketLink.objects.filter(link_type=TicketLink.TYPE_RELATES_TO)
            .filter(Q(source_ticket=self.instance) | Q(target_ticket=self.instance))
            .values_list("source_ticket_id", "target_ticket_id")
        )
        self.fields["relates_to_tickets"].initial = [
            target_id if source_id == self.instance.pk else source_id
            for source_id, target_id in raw_relates
        ]

    def clean_description(self):
        return sanitize_rich_text(self.cleaned_data.get("description", ""))

    def clean_tags_input(self):
        raw_value = self.cleaned_data.get("tags_input", "")
        tag_names = []
        seen = set()
        name_field = Tag._meta.get_field("name")

        for raw_name in re.split(r"[,;\n]+", raw_value):
            cleaned_name = " ".join(raw_name.split())
            if not cleaned_name:
                continue
            normalized_name = normalize_tag_name(cleaned_name)
            if normalized_name in seen:
                continue
            name_field.clean(cleaned_name, None)
            seen.add(normalized_name)
            tag_names.append(cleaned_name)

        self._cleaned_tag_names = tag_names
        return ", ".join(tag_names)

    def clean_initial_load(self):
        if self.instance.pk:
            return self.instance.initial_load
        return self.cleaned_data.get("initial_load", 0)

    def save(self, commit=True):
        ticket = super().save(commit=False)
        if self.instance.pk:
            ticket.initial_load = self.instance.initial_load
        if commit:
            ticket.save()
            self.save_m2m()
            ticket.tags.set(self._resolve_tags())
            self._sync_links(ticket)
        return ticket

    @staticmethod
    def _ticket_label(ticket):
        return f"#{ticket.pk} - {ticket.title}"

    def _resolve_tags(self):
        resolved = []
        for name in getattr(self, "_cleaned_tag_names", []):
            normalized = normalize_tag_name(name)
            tag = Tag.objects.filter(normalized_name=normalized).first()
            if tag is None:
                tag = Tag.objects.create(name=name)
            resolved.append(tag)
        return resolved

    def _sync_links(self, ticket):
        blocked_by = list(self.cleaned_data.get("blocked_by_tickets", []))
        relates_to = list(self.cleaned_data.get("relates_to_tickets", []))

        TicketLink.objects.filter(source_ticket=ticket, link_type=TicketLink.TYPE_BLOCKED_BY).delete()
        TicketLink.objects.bulk_create([
            TicketLink(source_ticket=ticket, target_ticket=t, link_type=TicketLink.TYPE_BLOCKED_BY)
            for t in blocked_by
        ])

        TicketLink.objects.filter(link_type=TicketLink.TYPE_RELATES_TO).filter(
            Q(source_ticket=ticket) | Q(target_ticket=ticket)
        ).delete()

        created_pairs = set()
        for related in relates_to:
            source_id, target_id = sorted([ticket.pk, related.pk])
            if (source_id, target_id) in created_pairs:
                continue
            created_pairs.add((source_id, target_id))
            TicketLink.objects.create(
                source_ticket_id=source_id,
                target_ticket_id=target_id,
                link_type=TicketLink.TYPE_RELATES_TO,
            )
