docker pull rabbitmq
docker build -t localhost/myemslcontroller .
docker build -t localhost/myemslcelery - < Dockerfile.celery
docker build -t localhost/myemsldjango - < Dockerfile.django
