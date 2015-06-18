docker pull rabbitmq
docker tag -f rabbitmq artifactory.pnnl.gov/myemslrabbit:$1
docker build -t localhost/myemslcontroller:$1 .
docker build -t artifactory.pnnl.gov/myemslcelery:$1 - < Dockerfile.celery
docker build -t artifactory.pnnl.gov/myemsldjango:$1 - < Dockerfile.django
