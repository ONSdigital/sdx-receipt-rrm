import logging
from structlog import wrap_logger
from app.async_consumer import AsyncConsumer
from app.response_processor import ResponseProcessor
from app import settings

logging.basicConfig(level=settings.LOGGING_LEVEL, format=settings.LOGGING_FORMAT)
logger = wrap_logger(logging.getLogger(__name__))


class Consumer(AsyncConsumer):
    def on_message(self, unused_channel, basic_deliver, properties, body):
        logger.info('Received message', delivery_tag=basic_deliver.delivery_tag, app_id=properties.app_id)

        processor = ResponseProcessor(logger)
        options = ResponseProcessor.options()

        try:
            message = body.decode("utf-8")
            processed_ok = processor.process(message, **options)

            if processed_ok:
                self.acknowledge_message(basic_deliver.delivery_tag, tx_id=processor.tx_id)

        except Exception as e:
            logger.error("ResponseProcessor failed", exception=e, tx_id=processor.tx_id)


def main():
    logger.debug("Starting consumer")
    consumer = Consumer()
    try:
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop()

if __name__ == '__main__':
    main()
