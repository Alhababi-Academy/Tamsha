import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text):
    """
    Converts Markdown text to HTML and marks it as safe.
    """
    html = markdown.markdown(text)
    return mark_safe(html)
