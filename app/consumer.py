import logging
from structlog import wrap_logger
from app.async_consumer import AsyncConsumer
from app.response_processor import ResponseProcessor, BadMessageError, RetryableError
from app import settings
import sys

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


class Consumer(AsyncConsumer):
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

        except BadMessageError as e:
            # If it's a bad message then we have to reject it
            logger.error("ResponseProcessor failed - bad message - rejecting", tx_id=processor.tx_id, delivery_count=delivery_count)
            self.reject_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)

        except RetryableError as e:
            logger.error("ResponseProcessor failed - nack for retry", exception=e, tx_id=processor.tx_id, delivery_count=delivery_count)
            self.nack_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)

        except Exception as e:
            # We don't know what happened but we'll be kind and allow a retry as
            # it's more than likely a local problem rather than a bad message
            logger.error("ResponseProcessor failed - unexpected - nack for retry", exception=e, tx_id=processor.tx_id, delivery_count=delivery_count)
            self.nack_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)


def main():
    logger.debug("Starting consumer")

    if settings.SDX_RECEIPT_RRM_SECRET is None:
        logger.error("No SDX_RECEIPT_RRM_SECRET env var supplied")
        sys.exit(1)

    consumer = Consumer()
    try:
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop()

if __name__ == '__main__':
    main()
