import os
import sys
from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "UploadServer.settings")

argv = []
argv.append('migrate')
argv.append('migrate')
print argv

execute_from_command_line(argv)
