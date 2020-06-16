import logging
import os

LOGGING_LEVEL = logging.getLevelName(os.getenv('LOGGING_LEVEL', 'DEBUG'))
LOGGING_FORMAT = "%(asctime)s.%(msecs)06dZ|%(levelname)s: sdx-receipt-rrm: %(message)s"

SECURITY_USER_NAME = os.getenv('RM_RECEIPT_SECURITY_USER_NAME', 'dummy_user')
SECURITY_USER_PASSWORD = os.getenv('RM_RECEIPT_SECURITY_USER_PASSWORD', 'dummy_password')
BASIC_AUTH = (SECURITY_USER_NAME, SECURITY_USER_PASSWORD)

RABBIT_QUARANTINE_QUEUE = 'rrm_receipt_quarantine'
RABBIT_QUEUE = 'rrm_receipt'
RABBIT_EXCHANGE = 'message'

SDX_RECEIPT_RRM_SECRET = os.getenv("SDX_RECEIPT_RRM_SECRET")
if SDX_RECEIPT_RRM_SECRET is not None:
    SDX_RECEIPT_RRM_SECRET = SDX_RECEIPT_RRM_SECRET.encode("ascii")

RM_SDX_GATEWAY_URL = os.getenv("RM_SDX_GATEWAY_URL", "http://sdx-mock-receipt:5000/receipts")
RM_SDX_GATEWAY_CERT_LOCATION = os.getenv("RM_SDX_GATEWAY_CERT_LOCATION", "path/to/ons.pem")

RABBIT_URL = 'amqp://{user}:{password}@{hostname}:{port}/{vhost}'.format(
    hostname=os.getenv('RABBITMQ_HOST', 'rabbit'),
    port=os.getenv('RABBITMQ_PORT', 5672),
    user=os.getenv('RABBITMQ_DEFAULT_USER', 'rabbit'),
    password=os.getenv('RABBITMQ_DEFAULT_PASS', 'rabbit'),
    vhost=os.getenv('RABBITMQ_DEFAULT_VHOST', '%2f')
)

RABBIT_URLS = [RABBIT_URL]
