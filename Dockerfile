FROM ubuntu:trusty

MAINTAINER david.brown@pnnl.gov

RUN apt-get update && apt-get -y dist-upgrade && apt-get install -y python-dev python-pip rabbitmq-server python-pycurl
RUN pip install django==1.7.7 celery psutil
RUN mkdir /app
ADD . /app
RUN chown -R daemon:nogroup -R /app
WORKDIR /app
EXPOSE 8000
CMD /bin/bash -xe startme.sh
