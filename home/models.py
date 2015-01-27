from django.db import models

class Filepath(models.Model):
    name = models.CharField(primary_key=True, max_length=80)
    fullpath = models.CharField(max_length=500)

class Metadata(models.Model):
    # display name
    label = models.CharField(primary_key=True,max_length=80)

    #searchable
    name = models.CharField(max_length=80)
