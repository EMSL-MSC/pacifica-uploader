# -*- coding: utf-8 -*-
from django import forms
#from django.db import models
#from django.test._doctest import DocFileCase
#from filebrowser.fields import FileBrowseField

class DocumentForm(forms.Form):
    docfile = forms.FileField(label='Select a file')