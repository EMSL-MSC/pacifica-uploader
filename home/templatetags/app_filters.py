'''
Created on Dec 3, 2014

@author: D3E889
'''
from django import template

register = template.Library()

@register.filter
def get_at_index(list, index):
    return list[index]