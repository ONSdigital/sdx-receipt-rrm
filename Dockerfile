FROM onsdigital/flask-crypto-queue

COPY app /app
COPY startup.sh /startup.sh
COPY requirements.txt /requirements.txt
COPY Makefile /Makefile

RUN mkdir -p /app/logs

RUN make build

ENTRYPOINT ./startup.sh
