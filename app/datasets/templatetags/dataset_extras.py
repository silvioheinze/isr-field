from django import template

register = template.Library()

@register.filter
def get_field_value(entry, field_name):
    """Get the value of a specific field for an entry"""
    try:
        field = entry.fields.get(field_name=field_name)
        return field.get_typed_value()
    except:
        return ''

@register.filter
def get_choices_list(field):
    """Get choices as a list for choice fields"""
    if field.field_type == 'choice' or field.typology:
        return field.get_choices_list()
    return []

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    return dictionary.get(key, '')
