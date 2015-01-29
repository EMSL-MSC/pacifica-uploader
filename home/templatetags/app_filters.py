'''
Created on Dec 3, 2014

@author: D3E889
'''
from django import template

register = template.Library()

@register.filter
def get_at_index(items, index):
    """
    custom filter to get an item from a list in the html build phase
    """

    return items[index]
