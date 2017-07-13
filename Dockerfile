FROM onsdigital/flask-crypto-queue

COPY app /app
COPY startup.sh /startup.sh

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -yq git gcc make build-essential python3-dev python3-reportlab
RUN git clone https://github.com/ONSdigital/sdx-common.git
RUN pip3 install ./sdx-common

RUN mkdir -p /app/logs

ENTRYPOINT ./startup.sh
