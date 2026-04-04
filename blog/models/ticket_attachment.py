from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from .ticket import Ticket

ALLOWED_IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp"]
MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to="attachments/",
        validators=[FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS)],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def clean(self):
        super().clean()
        if self.file and self.file.size > MAX_ATTACHMENT_SIZE_BYTES:
            raise ValidationError("Max file size: 5 MB.")

    def __str__(self):
        return f"Attachment for ticket #{self.ticket_id}"
