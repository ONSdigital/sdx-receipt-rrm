FROM onsdigital/flask-crypto-queue

COPY app /app
COPY startup.sh /startup.sh
COPY requirements.txt /app/requirements.txt
COPY Makefile /app/Makefile

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -yq git gcc make build-essential python3-dev python3-reportlab

RUN mkdir -p /app/logs

RUN make build

ENTRYPOINT ./startup.sh
