"""
register the Django models
"""

from django.contrib import admin
from home.models import Filepath
from home.models import Metadata

# Register your models here.
admin.site.register(Filepath)
admin.site.register(Metadata)
