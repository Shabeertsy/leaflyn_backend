from django import template

register = template.Library()

@register.filter
def percent_of(value, total):
    try:
        if total > 0:
            return round((value / total) * 100, 2)
        return 0
    except (ValueError, TypeError):
        return 0