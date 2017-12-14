# pylint: disable=no-member
# pylint: disable=invalid-name
# justification: because pylint doesn't get celery

"""
Celery properties
"""

from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UploadServer.settings')

# pylint: disable=wrong-import-position
from django.conf import settings  # noqa
# pylint: enable=wrong-import-position

app = Celery('UploadServer')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    """
    Celery boilerplate
    """
    print 'Request: {0!r}'.format(self.request)
