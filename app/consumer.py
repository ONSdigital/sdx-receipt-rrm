import logging
from structlog import wrap_logger
from app import __version__
from app.async_consumer import AsyncConsumer
from app.response_processor import ResponseProcessor
from app.helpers.exceptions import DecryptError, BadMessageError, RetryableError
from app import settings
from app.queue_publisher import QueuePublisher
import sys
import os

logging.basicConfig(level=settings.LOGGING_LEVEL, format=settings.LOGGING_FORMAT)
logger = wrap_logger(logging.getLogger(__name__))


def get_delivery_count_from_properties(properties):
    """
    Returns the delivery count for a message from the rabbit queue. The
    value is auto-set by rabbitmq.
    """
    delivery_count = 0
    if properties.headers and 'x-delivery-count' in properties.headers:
        delivery_count = properties.headers['x-delivery-count']
    return delivery_count + 1


def _get_value(key):
    value = os.getenv(key)
    if not value:
        raise ValueError("No value set for " + key)


def check_default_env_vars():

    env_vars = ["LOGGING_LEVEL", "RECEIPT_HOST", "RECEIPT_PATH", "RECEIPT_USER",
                "RECEIPT_PASS", "RABBITMQ_QUARANTINE_QUEUE", "RECEIPT_RRM_QUEUE", "RABBITMQ_EXCHANGE",
                "SDX_RECEIPT_RRM_SECRET", "RABBITMQ_HOST", "RABBITMQ_HOST2", "RABBITMQ_PORT",
                "RABBITMQ_PORT2", "RABBITMQ_DEFAULT_USER", "RABBITMQ_DEFAULT_PASS", "RABBITMQ_DEFAULT_VHOST"]

    for i in env_vars:
        try:
            _get_value(i)
        except ValueError as e:
            logger.error("Unable to start service", error=e)
            missing_env_var = True

    if missing_env_var is True:
        sys.exit(1)


class Consumer(AsyncConsumer):

    def __init__(self, **kwargs):
        super().__init__()
        self.quarantine_publisher = QueuePublisher(logger, settings.RABBIT_URLS, settings.RABBIT_QUARANTINE_QUEUE)

    def on_message(self, unused_channel, basic_deliver, properties, body):

        delivery_count = get_delivery_count_from_properties(properties)

        logger.info(
            'Received message',
            queue=self.QUEUE,
            delivery_tag=basic_deliver.delivery_tag,
            delivery_count=delivery_count,
            app_id=properties.app_id
        )

        processor = ResponseProcessor(logger)

        try:
            processor.process(body.decode("utf-8"))
            self.acknowledge_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)

        except DecryptError as e:
            # Throw it into the quarantine queue to be dealt with
            self.quarantine_publisher.publish_message(body)
            self.reject_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)
            logger.error("Bad decrypt", action="quarantined", exception=e, tx_id=processor.tx_id, delivery_count=delivery_count)

        except BadMessageError as e:
            # If it's a bad message then we have to reject it
            self.reject_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)
            logger.error("Bad message", action="rejected", exception=e, tx_id=processor.tx_id, delivery_count=delivery_count)

        except (RetryableError, Exception) as e:
            self.nack_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)
            logger.error("Failed to process", action="nack", exception=e, tx_id=processor.tx_id, delivery_count=delivery_count)


def main():
    logger.info("Starting consumer", version=__version__)

    check_default_env_vars()

    consumer = Consumer()
    try:
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop()

if __name__ == '__main__':
    main()
