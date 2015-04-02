#!/bin/bash -x

rabbitmq-server &
sleep 5
cd /app
#export DJANGO_SETTINGS_MODULE=UploadServer.settings_production
export PYTHONPATH=$PWD
su daemon -s /bin/bash -c 'cd /app; celery -A UploadServer worker --loglevel=info' &
su daemon -s /bin/bash -c 'cd /app; python manage.py migrate'
su daemon -s /bin/bash -c 'cd /app; python manage.py runserver 0.0.0.0:8000'
