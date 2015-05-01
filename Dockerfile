FROM ubuntu:trusty

MAINTAINER david.brown@pnnl.gov

RUN apt-get update && \
    apt-get -y dist-upgrade && \
    apt-get install -y \
      python-dev \
      python-pip \
      rabbitmq-server \
      python-pycurl \
      curl \
      sqlite3 \
      expect && \
    apt-get clean all
RUN pip install \
    django==1.7.7 \
    celery \
    psutil
RUN mkdir /app
ADD . /app
WORKDIR /app
ENV DJANGO_SETTINGS_MODULE UploadServer.settings_production
ENV PYTHONPATH /app
RUN python manage.py migrate
RUN ./setup-superuser
RUN chmod og+r /etc/resolv.conf
RUN chown -R 1:1 -R /app
