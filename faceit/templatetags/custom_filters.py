from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0 

@register.filter
def min_value(value, arg):
    """Returns the minimum of value and arg"""
    try:
        return min(float(value), float(arg))
    except (ValueError, TypeError):
        return value 