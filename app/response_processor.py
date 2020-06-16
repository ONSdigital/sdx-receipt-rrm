from json import loads

from cryptography.fernet import Fernet
from requests import Session
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from requests.packages.urllib3.exceptions import MaxRetryError
from requests.packages.urllib3.util.retry import Retry
from sdc.rabbit.exceptions import RetryableError, QuarantinableError

from app import settings
from app.helpers.exceptions import DecryptError


class ResponseProcessor:

    def __init__(self, logger):
        self.logger = logger
        self._retries = 5
        self.session = Session()
        retries = Retry(total=self._retries, backoff_factor=0.5)
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def process(self, message, tx_id=None):
        """Entry point for processing a message off the rabbit queue
        :param message  The message to be processed
        :param tx_id    The tx_id of the message, consistent across all of sdx services
        """
        self.logger = self.logger.bind(tx_id=tx_id)
        # Decrypt
        self.logger.info("Decrypting message")
        try:
            message = self._decrypt(token=message, secret=settings.SDX_RECEIPT_RRM_SECRET)
        except Exception:
            self.logger.exception("Exception decrypting message")
            raise DecryptError("Failed to decrypt")

        # Validate
        self.logger.info("Validating message")
        decrypted_json = loads(message)
        self._validate(decrypted_json, tx_id)

        # Send Receipt
        case_id = decrypted_json['case_id']
        user_id = decrypted_json['metadata']['user_id']
        tx_id = decrypted_json['tx_id']

        self.logger = self.logger.bind(tx_id=tx_id, case_id=case_id, user_id=user_id)
        self.logger.info("RM submission received")
        self._send_rm_receipt(case_id, user_id)

        # If we don't unbind these fields, their current value will be retained for the next
        # submission.  This leads to incorrect values being logged out in the bound fields.
        self.logger = self.logger.unbind("tx_id", "case_id", "user_id")

    def _decrypt(self, token, secret):
        f = Fernet(secret)
        try:
            message = f.decrypt(token)
        except TypeError:
            message = f.decrypt(token.encode("utf-8"))
        return message.decode("utf-8")

    def _validate(self, decrypted_json, tx_id):
        """Validate that tx_id, case_id and metadata elements are present,
        log an error for each one that is missing and then raise a QuarantinableError """

        if 'case_id' not in decrypted_json:
            self.logger.error("Decrypted json missing case_id. Quarantining message")
            raise QuarantinableError

        if 'metadata' not in decrypted_json:
            self.logger.error("Decrypted json missing metadata. Quarantining message")
            raise QuarantinableError

        if 'tx_id' not in decrypted_json:
            self.logger.error('Decrypted json missing tx_id . Quarantining message')
            raise QuarantinableError

        decrypted_tx_id = decrypted_json['tx_id']
        if tx_id and decrypted_tx_id != tx_id:
            self.logger.error('tx_ids from decrypted_json and message header do not match. Quarantining message',
                              decrypted_tx_id=decrypted_tx_id,
                              message_tx_id=tx_id)
            raise QuarantinableError

    def _send_rm_receipt(self, case_id, user_id):
        request_url = settings.RM_SDX_GATEWAY_URL
        location = settings.RM_SDX_GATEWAY_CERT_LOCATION
        request_json = {'caseId': case_id,
                        'userId': user_id}
        try:
            r = self.session.post(request_url, verify=location, auth=settings.BASIC_AUTH, json=request_json, timeout=60)
        except MaxRetryError:
            self.logger.error("Max retries exceeded (5)",
                              request_url=request_url)
            raise RetryableError
        except RequestException:
            self.logger.exception("Something unexpected went wrong connecting to the gateway",
                                  request_url=request_url)
            raise RetryableError

        if r.status_code == 201:
            self.logger.info("RM sdx gateway receipt creation was a success",
                             request_url=request_url)
            return

        elif 400 <= r.status_code < 500:
            self.logger.error("RM sdx gateway returned client error, unable to receipt",
                              request_url=request_url,
                              status=r.status_code)
            raise QuarantinableError
        else:
            self.logger.error("SDX --> RM receipting error - retrying",
                              request_url=request_url)
            raise RetryableError
