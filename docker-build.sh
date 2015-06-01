docker pull rabbitmq
docker tag rabbitmq artifactory.pnnl.gov/myemslrabbit
docker build -t localhost/myemslcontroller .
docker build -t artifactory.pnnl.gov/myemslcelery - < Dockerfile.celery
docker build -t artifactory.pnnl.gov/myemsldjango - < Dockerfile.django
