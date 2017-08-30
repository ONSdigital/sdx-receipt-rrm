from json import loads
import logging
import xml.etree.ElementTree as etree

from cryptography.fernet import Fernet
from requests.packages.urllib3.exceptions import MaxRetryError
from sdc.rabbit.exceptions import RetryableError, QuarantinableError
from structlog import wrap_logger

from app import receipt
from app import settings
from app.settings import session
from app.helpers.exceptions import ClientError, DecryptError

logger = wrap_logger(logging.getLogger(__name__))


class ResponseProcessor:

    def __init__(self, logger=logger):
        self.logger = logger
        self.tx_id = None

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
            logger.info('tx_ids from decrypted_json and message header do not match.' +
                        ' Rejecting message',
                        decrypted_tx_id=decrypted.get('tx_id'),
                        message_tx_id=self.tx_id)
            raise QuarantinableError
        self.tx_id = decrypted['tx_id']
        self.logger = self.logger.bind(tx_id=self.tx_id)

        if "metadata" not in decrypted:
            logger.info("Missing metadata")
            raise QuarantinableError
        return

    def _encode(self, decrypted):
        xml = receipt.get_receipt_xml(decrypted)
        if xml is None:
            logger.info("Unable to generate xml from message")
            raise QuarantinableError
        return xml

    def _send_receipt(self, decrypted, xml):
        endpoint = receipt.get_receipt_endpoint(decrypted)
        if endpoint is None:
            logger.info("Unable to determine delivery endpoint from message")
            raise QuarantinableError

        headers = receipt.get_receipt_headers()
        auth = (settings.RECEIPT_USER, settings.RECEIPT_PASS)

        res_logger = self.logger.bind(request_url=endpoint)

        try:
            res_logger.info("Calling external receipting service", service="External receipt")
            res = session.post(endpoint, data=xml, headers=headers, verify=False, auth=auth)

            res_logger = res_logger.bind(status=res.status_code)

            if res.status_code == 400:
                res_logger.error("Receipt rejected by endpoint")
                raise ClientError

            elif res.status_code == 404:
                namespaces = {'error': 'http://ns.ons.gov.uk/namespaces/resources/error'}
                tree = etree.fromstring(res.content)
                element = tree.find('error:message', namespaces).text
                elements = element.split('-')

                if elements[0] == '1009':
                    stat_unit_id = elements[-1].split('statistical_unit_id: ')[-1].split()[0]
                    collection_exercise_sid = elements[-1].split('collection_exercise_sid: ')[-1].split()[0]

                    res_logger.error("Receipt rejected by endpoint",
                                     msg="No records were found on the man_ce_sample_map table",
                                     error=1009,
                                     stat_unit_id=stat_unit_id,
                                     collection_exercise_sid=collection_exercise_sid)

                    raise ClientError

                else:
                    res_logger.error("Bad response from endpoint")
                    raise RetryableError

            elif res.status_code != 200 and res.status_code != 201:
                # Endpoint may be temporarily down
                res_logger.error("Bad response from endpoint")
                raise RetryableError

            else:
                res_logger.info("Sent receipt")

            return res

        except MaxRetryError:
            res_logger.error("Max retries exceeded (5) attempting to send to endpoint")
            raise RetryableError
