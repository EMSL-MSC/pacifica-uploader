#!/bin/bash -xe

sudo rm -f /usr/local/bin/docker-compose
sudo curl -L -o /usr/local/bin/docker-compose https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)
sudo chmod +x /usr/local/bin/docker-compose
sudo service postgresql stop

if [ "$RUN_LINTS" = "true" ]; then
  pip install pre-commit
else
  pip install codeclimate-test-reporter coverage nose pytest
fi

docker-compose build baseimage
docker-compose up -d
MAX_TRIES=60
HTTP_CODE=$(curl -sL -w "%{http_code}\\n" localhost:8121/keys -o /dev/null || true)
while [[ $HTTP_CODE != 200 && $MAX_TRIES > 0 ]] ; do
  sleep 1
  HTTP_CODE=$(curl -sL -w "%{http_code}\\n" localhost:8121/keys -o /dev/null || true)
  MAX_TRIES=$(( MAX_TRIES - 1 ))
done
docker run -it --rm --net=pacificauploader_default -e METADATA_URL=http://metadataserver:8121 -e PYTHONPATH=/usr/src/app pacifica/metadata python test_files/loadit.py
docker-compose stop uploaddjango uploadcelery uploadamqp
docker-compose stop policy
docker-compost start policy
