import logging
import sys
from structlog import wrap_logger

from sdc.rabbit import MessageConsumer
from sdc.rabbit import QueuePublisher

from app.response_processor import ResponseProcessor
import app.settings

logger = wrap_logger(logging.getLogger(__name__))


def run():
    logging.basicConfig(format=app.settings.LOGGING_FORMAT,
                        datefmt="%Y-%m-%dT%H:%M:%S",
                        level=app.settings.LOGGING_LEVEL)

    logging.getLogger("sdc.rabbit").setLevel(logging.DEBUG)

    response_processor = ResponseProcessor(logger)

    quarantine_publisher = QueuePublisher(
        urls=app.settings.RABBIT_URLS,
        queue=app.settings.RABBIT_QUARANTINE_QUEUE
    )
    message_consumer = MessageConsumer(
        durable_queue=True,
        exchange=app.settings.RABBIT_EXCHANGE,
        exchange_type="topic",
        rabbit_queue=app.settings.RABBIT_QUEUE,
        rabbit_urls=app.settings.RABBIT_URLS,
        quarantine_publisher=quarantine_publisher,
        process=response_processor.process
    )

    try:
        logger.info("Starting consumer")

        if app.settings.SDX_RECEIPT_RRM_SECRET is None:
            logger.error("No SDX_RECEIPT_RRM_SECRET env var supplied")
            sys.exit(1)
        message_consumer.run()
    except KeyboardInterrupt:
        message_consumer.stop()


if __name__ == '__main__':
    run()
