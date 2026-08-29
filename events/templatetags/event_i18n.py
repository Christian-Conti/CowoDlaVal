from django import template

from events.i18n import tr


register = template.Library()


@register.simple_tag
def event_t(key):
    return tr(key)
