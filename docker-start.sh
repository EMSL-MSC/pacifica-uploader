docker run -d -e RABBITMQ_NODENAME=testamqp --name testamqp rabbitmq
docker run -d -p 8000:8000 --link testamqp:amqp localhost/myemsldjango
docker run -d --link testamqp:amqp localhost/myemslcelery
