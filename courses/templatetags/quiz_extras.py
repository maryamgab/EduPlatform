from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    if not d:
        return ""
    # JSONField часто хранит ключи строками
    return d.get(str(key), d.get(key, ""))