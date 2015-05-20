docker pull rabbitmq
docker build -t localhost/myemslcontroller .
docker build -t artifactory.pnnl.gov/myemslcelery - < Dockerfile.celery
docker build -t artifactory.pnnl.gov/myemsldjango - < Dockerfile.django
