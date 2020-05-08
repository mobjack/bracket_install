FROM tiangolo/uvicorn-gunicorn:python3.7

RUN apt-get update
RUN apt-get install -y bash vim tcpdump net-tools
RUN pip install --upgrade pip

COPY ./app /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./app/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt