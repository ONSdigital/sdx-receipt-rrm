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

    @staticmethod
    def encrypt(message, secret):
        """
        Message may be a string or bytes.
        Secret key must be 32 url-safe base64-encoded bytes.

        """
        try:
            f = Fernet(secret)
        except ValueError:
            return None
        try:
            token = f.encrypt(message)
        except TypeError:
            token = f.encrypt(message.encode("utf-8"))
        return token

    @staticmethod
    def decrypt(token, secret):
        """
        Secret key must be 32 url-safe base64-encoded bytes or string

        Returned value is a string.
        """
        try:
            f = Fernet(secret)
        except ValueError:
            return None
        try:
            message = f.decrypt(token)
        except TypeError:
            message = f.decrypt(token.encode("utf-8"))
        return message.decode("utf-8")

    def __init__(self, logger):
        self.logger = logger
        self.tx_id = ""
        if settings.RECEIPT_HOST == "skip":
            self.skip_receipt = True
        else:
            self.skip_receipt = False

    def process(self, message, **kwargs):
        try:
            message = ResponseProcessor.decrypt(message, secret=settings.SDX_RECEIPT_RRM_SECRET)
        except Exception:
            # Key may be misconfigured, so allow a retry
            raise RetryableError("Failed to decrypt message")

        print("MESSAGE UN ENCRYPTED " + message)

        decrypted_json = loads(message)
        if "metadata" not in decrypted_json:
            raise BadMessageError("Missing metadata")

        metadata = decrypted_json['metadata']
        self.logger = self.logger.bind(user_id=metadata['user_id'], ru_ref=metadata['ru_ref'])

        if 'tx_id' not in decrypted_json:
            raise BadMessageError("Missing tx_id")

        self.tx_id = decrypted_json['tx_id']
        self.logger = self.logger.bind(tx_id=self.tx_id)

        return self.send_receipt(decrypted_json)

    def send_receipt(self, decrypted_json):
        if self.skip_receipt:
            self.logger.debug("Skipping sending receipt to RRM")
            return True
        else:
            self.logger.debug("Sending receipt to RRM")

        endpoint = receipt.get_receipt_endpoint(decrypted_json)
        if endpoint is None:
            raise BadMessageError("Unable to determine delivery endpoint from message")

        xml = receipt.get_receipt_xml(decrypted_json)
        if xml is None:
            raise BadMessageError("Unable to generate xml from message")

        headers = receipt.get_receipt_headers()

        response = self.remote_call(
            endpoint,
            data=xml.encode("utf-8"),
            headers=headers,
            verify=False,
            auth=(settings.RECEIPT_USER, settings.RECEIPT_PASS))

        if self.response_ok(response):
            self.logger.info("Message sent to endpoint")
            return True

    def remote_call(self, request_url, json=None, data=None, headers=None, verify=True, auth=None):
        try:
            self.logger.info("Calling service", request_url=request_url)
            r = None

            if data:
                r = session.post(request_url, data=data, headers=headers, verify=verify, auth=auth)
            else:
                r = session.get(request_url, headers=headers, verify=verify, auth=auth)
            return r

        except MaxRetryError:
            self.logger.error("Max retries exceeded (5)", request_url=request_url)

    def response_ok(self, res):
        if res.status_code == 400:
            raise BadMessageError("Rejected by endpoint", request_url=res.url, status_code=400)

        elif res.status_code != 200 and res.status_code != 201:
            # Endpoint may be temporarily down
            raise RetryableError("Bad response from endpoint", request_url=res.url, status_code=res.status_code)

        else:
            self.logger.info("Returned from service", request_url=res.url, status_code=res.status_code)
            return True
