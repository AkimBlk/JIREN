from django.test import SimpleTestCase

from blog.rich_text import sanitize_rich_text


class RichTextBehaviorTests(SimpleTestCase):
    def test_plain_text_is_wrapped_into_paragraphs_and_line_breaks(self):
        value = "First line\nSecond line\n\nThird block"

        sanitized = sanitize_rich_text(value)

        self.assertEqual(sanitized, "<p>First line<br>Second line</p><p>Third block</p>")

    def test_javascript_links_are_removed_but_safe_links_are_preserved(self):
        unsafe = '<a href="javascript:alert(1)">Unsafe</a>'
        safe = '<a href="/tickets/1" title="Open">Open</a>'

        self.assertEqual(sanitize_rich_text(unsafe), "<a>Unsafe</a>")
        self.assertEqual(
            sanitize_rich_text(safe),
            '<a href="/tickets/1" target="_blank" rel="noopener noreferrer" title="Open">Open</a>',
        )

    def test_data_image_sources_are_allowed_while_invalid_image_sources_are_removed(self):
        valid_image = '<img src="data:image/png;base64,AAAA" alt="Preview">'
        invalid_image = '<img src="ftp://example.com/image.png" alt="Preview">'

        self.assertEqual(
            sanitize_rich_text(valid_image),
            '<img src="data:image/png;base64,AAAA" alt="Preview">',
        )
        self.assertEqual(sanitize_rich_text(invalid_image), "")

    def test_disallowed_tags_and_their_content_are_skipped(self):
        value = '<p>Hello<script>alert(1)</script><strong>world</strong></p>'

        self.assertEqual(sanitize_rich_text(value), "<p>Hello<strong>world</strong></p>")

    def test_unbalanced_markup_is_closed_consistently(self):
        value = "<div><strong>Hello</div>"

        self.assertEqual(sanitize_rich_text(value), "<div><strong>Hello</strong></div>")
