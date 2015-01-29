"""
Django models, data structures supported in the Django database
"""

from django.db import models

class Filepath(models.Model):
    """
    Filepaths used by the application.
    Source directory, target directory, etc.
    """

    name = models.CharField(primary_key=True, max_length=80)
    fullpath = models.CharField(max_length=500)

class Metadata(models.Model):
    """
    Metadata specific to an instrument.
    label is the identifier seen by the user
    name is the identifier recognized by the backend
    """

    # display name
    label = models.CharField(primary_key=True, max_length=80)

    #searchable
    name = models.CharField(max_length=80)
