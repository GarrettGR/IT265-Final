#!/bin/bash
app="astro-sos"
docker stop ${app} || true && docker rm ${app} || true
docker build -t ${app} .
docker run -d -p 56733:80 \
  --name=${app} \
  -v $PWD:/app ${app}

docker logs -f ${app}