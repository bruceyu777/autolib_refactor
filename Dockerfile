FROM ubuntu:22.04
RUN apt-get update && apt-get install -y telnet ssh

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app
ENV TZ America/Vancouver
WORKDIR /app
COPY . /app
RUN apt-get -y update
RUN apt-get install -y python3-pip
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
CMD /bin/bash