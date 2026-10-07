import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


HTML_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?>")
IMAGE_DATA_URL_RE = re.compile(
    r"^data:image/(?:png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=\s]+$",
    re.IGNORECASE,
)

ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "u",
    "ul",
}
VOID_TAGS = {"br", "img"}
SKIP_CONTENT_TAGS = {"embed", "iframe", "object", "script", "style"}


def _paragraphize_plain_text(value):
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    paragraphs = []
    for block in re.split(r"\n{2,}", normalized):
        stripped_block = block.strip()
        if not stripped_block:
            continue
        paragraphs.append(f"<p>{escape(stripped_block).replace(chr(10), '<br>')}</p>")

    return "".join(paragraphs)


def _sanitize_url(value, allow_image_data=False):
    cleaned_value = str(value or "").strip()
    if not cleaned_value:
        return ""

    if allow_image_data and IMAGE_DATA_URL_RE.match(cleaned_value):
        return cleaned_value.replace("\n", "").replace("\r", "")

    if cleaned_value.startswith(("/", "#")):
        return cleaned_value

    parsed = urlparse(cleaned_value)
    if not parsed.scheme and not parsed.netloc:
        return cleaned_value

    if parsed.scheme.lower() in {"http", "https", "mailto"}:
        return cleaned_value

    return ""


class RichTextSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.open_tags = []
        self.skip_content_depth = 0

    def handle_starttag(self, tag, attrs):
        normalized_tag = tag.lower()

        if normalized_tag in SKIP_CONTENT_TAGS:
            self.skip_content_depth += 1
            return

        if self.skip_content_depth or normalized_tag not in ALLOWED_TAGS:
            return

        serialized_attrs = self._serialize_attrs(normalized_tag, attrs)
        if serialized_attrs is None:
            return
        self.parts.append(f"<{normalized_tag}{serialized_attrs}>")
        if normalized_tag not in VOID_TAGS:
            self.open_tags.append(normalized_tag)

    def handle_startendtag(self, tag, attrs):
        normalized_tag = tag.lower()

        if normalized_tag in SKIP_CONTENT_TAGS or self.skip_content_depth:
            return

        if normalized_tag not in ALLOWED_TAGS:
            return

        serialized_attrs = self._serialize_attrs(normalized_tag, attrs)
        if serialized_attrs is None:
            return
        self.parts.append(f"<{normalized_tag}{serialized_attrs}>")
        if normalized_tag not in VOID_TAGS:
            self.parts.append(f"</{normalized_tag}>")

    def handle_endtag(self, tag):
        normalized_tag = tag.lower()

        if normalized_tag in SKIP_CONTENT_TAGS:
            if self.skip_content_depth:
                self.skip_content_depth -= 1
            return

        if self.skip_content_depth or normalized_tag not in ALLOWED_TAGS or normalized_tag in VOID_TAGS:
            return

        if normalized_tag not in self.open_tags:
            return

        while self.open_tags:
            open_tag = self.open_tags.pop()
            self.parts.append(f"</{open_tag}>")
            if open_tag == normalized_tag:
                break

    def handle_data(self, data):
        if not self.skip_content_depth and data:
            self.parts.append(escape(data))

    def get_html(self):
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")
        return "".join(self.parts)

    def _serialize_attrs(self, tag, attrs):
        serialized = []
        attrs_dict = dict(attrs)

        if tag == "a":
            href = _sanitize_url(attrs_dict.get("href"))
            if href:
                serialized.append(("href", href))
                serialized.append(("target", "_blank"))
                serialized.append(("rel", "noopener noreferrer"))
            title = str(attrs_dict.get("title", "")).strip()
            if title:
                serialized.append(("title", title))

        if tag == "img":
            src = _sanitize_url(attrs_dict.get("src"), allow_image_data=True)
            if not src:
                return None
            serialized.append(("src", src))
            alt = str(attrs_dict.get("alt", "")).strip()
            if alt:
                serialized.append(("alt", alt))

        return "".join(f' {name}="{escape(value, quote=True)}"' for name, value in serialized)


def sanitize_rich_text(value):
    if not value:
        return ""

    string_value = str(value)
    if not HTML_TAG_RE.search(string_value):
        return _paragraphize_plain_text(string_value)

    sanitizer = RichTextSanitizer()
    sanitizer.feed(string_value)
    sanitizer.close()
    sanitized = sanitizer.get_html().strip()
    return sanitized
