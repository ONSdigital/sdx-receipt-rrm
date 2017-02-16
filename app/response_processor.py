from json import loads

from app import receipt
from app import settings
from app.settings import session

from cryptography.fernet import Fernet
from requests.packages.urllib3.exceptions import MaxRetryError
from app.helpers.exceptions import DecryptError, BadMessageError, RetryableError


class ResponseProcessor:

    def __init__(self, logger):
        self.logger = logger
        self.tx_id = ""

    def process(self, message):

        # Decrypt
        try:
            message = self._decrypt(token=message, secret=settings.SDX_RECEIPT_RRM_SECRET)
        except Exception as e:
            self.logger.error("Exception decrypting message", exception=e)
            raise DecryptError("Failed to decrypt")

        # Validate
        decrypted_json = loads(message)
        self._validate(decrypted_json)

        # Encode
        xml = self._encode(decrypted_json)

        # Send
        self._send_receipt(decrypted_json, xml)

        return

    def _decrypt(self, token, secret):
        f = Fernet(secret)
        try:
            message = f.decrypt(token)
        except TypeError:
            message = f.decrypt(token.encode("utf-8"))
        return message.decode("utf-8")

    def _validate(self, decrypted):
        if 'tx_id' not in decrypted:
            raise BadMessageError("Missing tx_id")
        self.tx_id = decrypted['tx_id']
        self.logger = self.logger.bind(tx_id=self.tx_id)

        if "metadata" not in decrypted:
            raise BadMessageError("Missing metadata")
        return

    def _encode(self, decrypted):
        xml = receipt.get_receipt_xml(decrypted)
        if xml is None:
            raise BadMessageError("Unable to generate xml from message")
        return xml

    def _send_receipt(self, decrypted, xml):
        endpoint = receipt.get_receipt_endpoint(decrypted)
        if endpoint is None:
            raise BadMessageError("Unable to determine delivery endpoint from message")

        headers = receipt.get_receipt_headers()
        auth = (settings.RECEIPT_USER, settings.RECEIPT_PASS)

        res_logger = self.logger.bind(request_url=endpoint)

        try:
            res_logger.info("Calling service")
            res = session.post(endpoint, data=xml, headers=headers, verify=False, auth=auth)

            res_logger = res_logger.bind(stats_code=res.status_code)

            if res.status_code == 400:
                res_logger.error("Receipt rejected by endpoint")
                raise BadMessageError("Failure to send receipt")

            elif res.status_code != 200 and res.status_code != 201:
                # Endpoint may be temporarily down
                res_logger.error("Bad response from endpoint")
                raise RetryableError("Bad response from endpoint")

            else:
                res_logger.info("Sent receipt")
                return

        except MaxRetryError:
            res_logger.error("Max retries exceeded (5) attempting to send to endpoint")
            raise RetryableError("Failure to send receipt")
