import logging
import os
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

LOGGING_FORMAT = "%(asctime)s|%(levelname)s: sdx-receipt-rrm: %(message)s"
LOGGING_LEVEL = logging.getLevelName(os.getenv('LOGGING_LEVEL', 'DEBUG'))

RECEIPT_HOST = os.getenv("RECEIPT_HOST", "http://sdx-mock-receipt:5000")
RECEIPT_PATH = os.getenv("RECEIPT_PATH", "reportingunits")
RECEIPT_USER = os.getenv("RECEIPT_USER", "")
RECEIPT_PASS = os.getenv("RECEIPT_PASS", "")

RABBIT_QUEUE = os.getenv('RABBITMQ_QUEUE', 'rrm_receipt')
RABBIT_QUARANTINE_QUEUE = os.getenv('RABBITMQ_QUEUE', 'rrm_receipt_quarantine')
RABBIT_EXCHANGE = os.getenv('RABBITMQ_EXCHANGE', 'message')

SDX_RECEIPT_RRM_SECRET = os.getenv("SDX_RECEIPT_RRM_SECRET")
if SDX_RECEIPT_RRM_SECRET is not None:
    SDX_RECEIPT_RRM_SECRET = SDX_RECEIPT_RRM_SECRET.encode("ascii")

RABBIT_URL = 'amqp://{user}:{password}@{hostname}:{port}/{vhost}'.format(
    hostname=os.getenv('RABBITMQ_HOST', 'rabbit'),
    port=os.getenv('RABBITMQ_PORT', 5672),
    user=os.getenv('RABBITMQ_DEFAULT_USER', 'rabbit'),
    password=os.getenv('RABBITMQ_DEFAULT_PASS', 'rabbit'),
    vhost=os.getenv('RABBITMQ_DEFAULT_VHOST', '%2f')
)

RABBIT_URL2 = 'amqp://{user}:{password}@{hostname}:{port}/{vhost}'.format(
    hostname=os.getenv('RABBITMQ_HOST2', 'rabbit'),
    port=os.getenv('RABBITMQ_PORT2', 5672),
    user=os.getenv('RABBITMQ_DEFAULT_USER', 'rabbit'),
    password=os.getenv('RABBITMQ_DEFAULT_PASS', 'rabbit'),
    vhost=os.getenv('RABBITMQ_DEFAULT_VHOST', '%2f')
)

RABBIT_URLS = [RABBIT_URL, RABBIT_URL2]

# Configure the number of retries attempted before failing call
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1)
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))
