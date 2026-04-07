import re

from django import forms
from django.db.models import Q

from .project import RichTextTextarea
from ..models import Tag, Ticket, TicketLink
from ..models.tag import normalize_tag_name
from ..rich_text import sanitize_rich_text


# Description templates by issue type
TICKET_TEMPLATES = {
    "story": """📖 USER STORY (As... I want... so that...)

As a <role/persona>,
I want <action/feature>,
so that <benefit/value>.

✅ ACCEPTANCE CRITERIA:
- Criteria 1: ...
- Criteria 2: ...
- Criteria 3: ...

📎 RESOURCES / REFERENCES:
- Link 1: ...

🎯 NOTES:
...""",

    "bug": """🐛 BUG REPORT

🔍 CONTEXT:
- Environment: (dev/staging/prod)
- Browser/Version: 
- Steps: ...

❌ PROBLEM:
What is not working correctly?

✅ EXPECTED BEHAVIOR:
What should happen instead?

📸 ACTUAL RESULT:
What did you observe? (screenshot/error)

🔄 STEPS TO REPRODUCE:
1. ...
2. ...
3. ...

💾 ADDITIONAL INFORMATION:
- App version: 
- Error log: ...""",

    "task": """☑️ TASK (Technical work)

📋 DESCRIPTION:
What do we need to do?

🎯 OBJECTIVE:
What is the expected outcome?

📝 ITEMS TO COVER:
- [ ] Item 1
- [ ] Item 2
- [ ] Item 3

⚙️ TECHNICAL DETAILS:
- Files to modify: ...
- Dependencies: ...

📎 REFERENCES:
- PR: ...
- Documentation: ...""",

    "epic": """🏔️ EPIC (Major initiative)

📖 DESCRIPTION:
What is this epic about?

🎯 OBJECTIVES:
- Objective 1: ...
- Objective 2: ...

📝 USER STORIES INCLUDED:
- US#1: ...
- US#2: ...

⏱️ TIMELINE:
- Phase 1: ...
- Phase 2: ...

📊 SUCCESS METRICS:
- Metric 1: ...
- Metric 2: ...""",
}


class TicketForm(forms.ModelForm):
    tags_input = forms.CharField(
        label="Tags",
        required=False,
    )
    blocked_by_tickets = forms.ModelMultipleChoiceField(
        queryset=Ticket.objects.none(),
        required=False,
        label="Blocked by",
        widget=forms.SelectMultiple(attrs={"class": "form-control", "size": 6}),
    )
    relates_to_tickets = forms.ModelMultipleChoiceField(
        queryset=Ticket.objects.none(),
        required=False,
        label="Relates to",
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
            "issue_type": forms.RadioSelect(),
            "description": RichTextTextarea(attrs={
                "rows": 10,
                "data-rich-text-source": "true",
                "class": "tw-w-full tw-px-3 tw-py-2 tw-border tw-border-[var(--helb-outline-variant)] tw-rounded tw-bg-[var(--helb-surface-container-low)] tw-text-[var(--helb-on-surface)] tw-text-sm focus:tw-outline-none focus:tw-border-[var(--helb-primary)] focus:tw-ring-1 focus:tw-ring-[var(--helb-primary)]",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None
        self.fields["blocked_by_tickets"].label_from_instance = self._ticket_label
        self.fields["relates_to_tickets"].label_from_instance = self._ticket_label

        if self.instance.pk:
            self._init_tags_field()
            self._init_link_fields()
            self.fields["initial_load"].disabled = True
            self.fields["initial_load"].help_text = None

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

    def clean_story_points(self):
        story_points = self.cleaned_data.get("story_points")
        project = self.cleaned_data.get("project")

        if not story_points or not project:
            return story_points

        from ..models import StoryPointsScheme
        scheme, _ = StoryPointsScheme.objects.get_or_create(project=project)

        if not scheme.is_valid(story_points):
            allowed = scheme.get_allowed_values()
            raise forms.ValidationError(
                f"Story points must be one of: {allowed}. "
                f"Current scheme: {scheme.scheme_type}"
            )

        return story_points

    def save(self, commit=True):
        ticket = super().save(commit=False)
        if self.instance.pk:
            ticket.initial_load = self.instance.initial_load
        if commit:
            ticket.save()
            self.save_m2m()
            ticket.tags.set(self._resolve_tags(ticket))
            self._sync_links(ticket)
        return ticket

    @staticmethod
    def _ticket_label(ticket):
        return f"#{ticket.pk} - {ticket.title}"

    def _resolve_tags(self, ticket):
        resolved = []
        for name in getattr(self, "_cleaned_tag_names", []):
            normalized = normalize_tag_name(name)
            tag = Tag.objects.filter(
                project=ticket.project,
                normalized_name=normalized
            ).first()
            if tag is None:
                tag = Tag.objects.create(
                    name=name,
                    project=ticket.project
                )
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