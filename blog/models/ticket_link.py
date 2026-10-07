from django.core.exceptions import ValidationError
from django.db import models

from .ticket import Ticket


class TicketLink(models.Model):
    TYPE_BLOCKED_BY = "BLOCKED_BY"
    TYPE_RELATES_TO = "RELATES_TO"
    LINK_TYPE_CHOICES = [
        (TYPE_BLOCKED_BY, "Blocked by"),
        (TYPE_RELATES_TO, "Relates to"),
    ]

    source_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="outgoing_links")
    target_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="incoming_links")
    link_type = models.CharField(max_length=20, choices=LINK_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["link_type", "source_ticket_id", "target_ticket_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_ticket", "target_ticket", "link_type"],
                name="unique_ticket_link",
            ),
        ]

    def clean(self):
        super().clean()
        self._normalize_direction()

        errors = {}

        if self.source_ticket_id == self.target_ticket_id:
            errors["target_ticket"] = "Cannot link ticket to itself."

        if (
            self.source_ticket_id
            and self.target_ticket_id
            and self.source_ticket.project_id != self.target_ticket.project_id
        ):
            errors["target_ticket"] = "Linked tickets must be in same project."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self._normalize_direction()
        super().save(*args, **kwargs)

    def _normalize_direction(self):
        if (
            self.link_type == self.TYPE_RELATES_TO
            and self.source_ticket_id
            and self.target_ticket_id
            and self.source_ticket_id > self.target_ticket_id
        ):
            self.source_ticket_id, self.target_ticket_id = (
                self.target_ticket_id,
                self.source_ticket_id,
            )

    def other_ticket(self, ticket):
        if ticket.pk == self.source_ticket_id:
            return self.target_ticket
        return self.source_ticket

    def __str__(self):
        return f"{self.source_ticket_id} {self.link_type} {self.target_ticket_id}"
