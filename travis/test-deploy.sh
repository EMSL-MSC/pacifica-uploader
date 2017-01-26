#!/bin/bash -xe
docker build -t pacifica/uploader:latest .
docker build -f Dockerfile.django -t pacifica/uploader-frontend:latest .
docker build -f Dockerfile.celery -t pacifica/uploader-backend:latest .
