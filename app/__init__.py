from sdx.common.logger_config import logger_initial_config

from app import settings

logger_initial_config(service_name='sdx-receipt-rrm',
                      log_level=settings.LOGGING_LEVEL)

__version__ = "2.3.0"
