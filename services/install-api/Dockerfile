FROM tiangolo/uvicorn-gunicorn:python3.7

#RUN apt-get update
#RUN apt-get install -y bash vim tcpdump net-tools
RUN pip install --upgrade pip

COPY ./app /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./app/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
#RUN ln -sf /app /var/www/app
######

# install dependencies
#RUN set -eux \
#    && apk add --no-cache --virtual .build-deps build-base /\
#        libressl-dev libffi-dev gcc musl-dev python3-dev \
#    && pip install --upgrade pip setuptools wheel \
#    && pip install -r /usr/src/app/requirements.txt \
#    && rm -rf /root/.cache/pip

# copy project
#COPY . /usr/src/app/