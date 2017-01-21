#pylint: disable=invalid-name
#justification: because pylint doesn't get django

"""
WSGI config for UploadServer project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "UploadServer.settings")
# pylint: disable=wrong-import-position
from django.core.wsgi import get_wsgi_application
# pylint: enable=wrong-import-position
application = get_wsgi_application()
