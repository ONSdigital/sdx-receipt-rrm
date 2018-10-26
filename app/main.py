import logging
import sys
from structlog import wrap_logger

from sdc.rabbit import MessageConsumer
from sdc.rabbit import QueuePublisher

from app.response_processor import ResponseProcessor
from app import settings, __version__

logger = wrap_logger(logging.getLogger(__name__))


def run():
    logging.basicConfig(format=settings.LOGGING_FORMAT,
                        datefmt="%Y-%m-%dT%H:%M:%S",
                        level=settings.LOGGING_LEVEL)

    logging.getLogger("sdc.rabbit").setLevel(logging.DEBUG)

    logger.info("Starting SDX Receipt RRM", version=__version__)

    response_processor = ResponseProcessor(logger)

    quarantine_publisher = QueuePublisher(
        urls=settings.RABBIT_URLS,
        queue=settings.RABBIT_QUARANTINE_QUEUE
    )

    message_consumer = MessageConsumer(
        durable_queue=True,
        exchange=settings.RABBIT_EXCHANGE,
        exchange_type="topic",
        rabbit_queue=settings.RABBIT_QUEUE,
        rabbit_urls=settings.RABBIT_URLS,
        quarantine_publisher=quarantine_publisher,
        process=response_processor.process
    )

    try:
        logger.info("Starting consumer")

        if settings.SDX_RECEIPT_RRM_SECRET is None:
            logger.error("No SDX_RECEIPT_RRM_SECRET env var supplied")
            sys.exit(1)
        message_consumer.run()
    except KeyboardInterrupt:
        message_consumer.stop()


if __name__ == '__main__':
    run()
