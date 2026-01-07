from django import template

register = template.Library()

@register.filter
def split_tags(value, delimiter=','):
    """
    Split a string by delimiter and return list of stripped tags
    usage: {{ scrape.tags|split_tags:"," }}
    """
    if not value:
        return []
    
    # split by delimiter and strip whitespace from each tag
    tags = [tag.strip() for tag in value.split(delimiter) if tag.strip()]
    return tags
