from django import template
from django.utils.safestring import mark_safe

from blog.rich_text import sanitize_rich_text


register = template.Library()


@register.filter
def render_ticket_description(value):
    sanitized_value = sanitize_rich_text(value)
    if not sanitized_value:
        return "No description."
    return mark_safe(sanitized_value)
