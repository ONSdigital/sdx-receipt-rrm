from json import loads

from app import receipt
from app import settings
from app.settings import session

from cryptography.fernet import Fernet
from requests.packages.urllib3.exceptions import MaxRetryError


class BadMessageError(Exception):
    # A bad message is broken in some way that will never be accepted by
    # the endpoing and as such should be rejected (it will still be logged
    # and stored so no data is lost)
    pass


class RetryableError(Exception):
    # A retryable error is apparently transient and may be due to temporary
    # network issues or misconfiguration, but the message is valid and should
    # be retried
    pass


class ResponseProcessor:

    def __init__(self, logger):
        self.logger = logger
        self.tx_id = ""

    def process(self, message):

        # Decrypt
        try:
            message = self._decrypt(token=message, secret=settings.SDX_RECEIPT_RRM_SECRET)
        except Exception as e:
            self.logger.exception("Exception decrypting message", exception=e)
            raise RetryableError("Failed to decrypt message")

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
            try:
                message = f.decrypt(token)
            except TypeError:
                message = f.decrypt(token.encode("utf-8"))
        except Exception:
            # If anything is ary, wrap it in a BadMessageError
            raise BadMessageError
        return message.decode("utf-8")

    def _validate(self, decrypted):
        if 'tx_id' not in decrypted:
            raise BadMessageError("Missing tx_id")
        self.logger.bind(tx_id=decrypted['tx_id'])

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

        try:
            self.logger.info("Calling service", request_url=endpoint)
            res = session.post(endpoint, data=xml, headers=headers, verify=False, auth=auth)

            if res.status_code == 400:
                self.logger.error("Receipt rejected by endpoint", request_url=res.url, status_code=400)
                raise BadMessageError("Failure to send receipt")

            elif res.status_code != 200 and res.status_code != 201:
                # Endpoint may be temporarily down
                self.logger.error("Bad response from endpoint", request_url=res.url, status_code=res.status_code)
                raise RetryableError("Failure to send receipt")

            else:
                self.logger.info("Returned from service", request_url=res.url, status_code=res.status_code)
                return

        except MaxRetryError:
            self.logger.error("Max retries exceeded (5) attempting to send to endpoint", request_url=endpoint)
            raise RetryableError("Failure to send receipt")
