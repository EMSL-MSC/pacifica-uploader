# -*- coding: utf-8 -*-

"""Django boilerplate"""

from django import forms


class DocumentForm(forms.Form):
    """
    Django boilerplate
    """
    docfile = forms.FileField(label='Select a file')
