from django import template

register = template.Library()

@register.simple_tag()
def dump_object(var):
    return vars(var)