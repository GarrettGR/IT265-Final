# syntax = docker/dockerfile:1

FROM tiangolo/uwsgi-nginx-flask:python3.11

# RUN apk --update add bash nano

ENV STATIC_URL /static
ENV STATIC_PATH /var/www/app/static

COPY ./requirements.txt /var/www/requirements.txt
COPY ./uwsgi.ini /var/www/uwsgi.ini 

RUN pip install -r /var/www/requirements.txt
