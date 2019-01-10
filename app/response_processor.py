from json import loads
import logging

from cryptography.fernet import Fernet
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import MaxRetryError
from requests.packages.urllib3.util.retry import Retry
from sdc.rabbit.exceptions import RetryableError, QuarantinableError
from structlog import wrap_logger

from app import settings
from app.helpers.exceptions import DecryptError

logger = wrap_logger(logging.getLogger(__name__))


class ResponseProcessor:

    def __init__(self, logger=logger):
        self.logger = logger
        self.tx_id = None
        self._retries = 5
        self.session = Session()
        retries = Retry(total=self._retries, backoff_factor=0.5)
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def process(self, message, tx_id=None):
        self.logger = self.logger.bind(tx_id=tx_id)

        # Decrypt
        try:
            message = self._decrypt(token=message, secret=settings.SDX_RECEIPT_RRM_SECRET)
        except Exception:
            self.logger.exception("Exception decrypting message")
            raise DecryptError("Failed to decrypt")

        # Validate
        decrypted_json = loads(message)
        self._validate(decrypted_json)

        # Send Receipt
        case_id = decrypted_json['case_id']
        user_id = decrypted_json['metadata']['user_id']
        self.logger.info("RM submission received", case_id=case_id)
        self._send_rm_receipt(case_id, user_id)

    def _decrypt(self, token, secret):
        f = Fernet(secret)
        try:
            message = f.decrypt(token)
        except TypeError:
            message = f.decrypt(token.encode("utf-8"))
        return message.decode("utf-8")

    def _validate(self, decrypted_json):
        if 'tx_id' not in decrypted_json:
            logger.error('tx_ids from decrypted_json and message header do not match. Quarantining message',
                         decrypted_tx_id=decrypted_json.get('tx_id'),
                         message_tx_id=self.tx_id)
            raise QuarantinableError
        if 'case_id' not in decrypted_json:
            logger.error("Missing case_id. Quarantining message")
            raise QuarantinableError
        if 'metadata' not in decrypted_json:
            logger.error("Missing metadata. Quarantining message")
            raise QuarantinableError

        self.tx_id = decrypted_json['tx_id']
        return

    def _send_rm_receipt(self, case_id, user_id):
        request_url = settings.RM_SDX_GATEWAY_URL
        request_json = {'caseId': case_id,
                        'userId': user_id}
        try:
            r = self.session.post(request_url, auth=settings.BASIC_AUTH, json=request_json)
        except MaxRetryError:
            logger.error("Max retries exceeded (5)",
                         request_url=request_url,
                         case_id=case_id)
            raise RetryableError

        if r.status_code == 201:
            logger.info("RM sdx gateway receipt creation was a success",
                        request_url=request_url,
                        case_id=case_id)
            return

        elif 400 <= r.status_code < 500:
            logger.error("RM sdx gateway returned client error, unable to receipt",
                         request_url=request_url,
                         status=r.status_code,
                         case_id=case_id)
            raise QuarantinableError
        else:
            logger.error("SDX --> RM receipting error - retrying",
                         request_url=request_url,
                         case_id=case_id)
            raise RetryableError
