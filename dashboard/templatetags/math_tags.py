# your_app/templatetags/math_tags.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply two numbers."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def divide(value, arg):
    """Divide two numbers, handling division by zero."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return value