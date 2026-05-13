# billing_app/templatetags/custom_tags.py

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key)
    return None


@register.filter
def subtract(value, arg):
    return int(value) - int(arg)


@register.filter
def row_count(variants):

    total = 0

    if not variants:
        return 0

    for v in variants:

        # dict access
        size = v.get("size")
        column = v.get("column")

        # only price
        if size == column:
            total += 1

        # size + price
        else:
            total += 2

    return total