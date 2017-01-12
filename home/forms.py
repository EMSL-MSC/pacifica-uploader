# -*- coding: utf-8 -*-


"""Django boilerplate"""

from django import forms

# pylint: disable=too-few-public-methods
# justification: django

class DocumentForm(forms.Form):
    """
    Django boilerplate
    """
    docfile = forms.FileField(label='Select a file')
