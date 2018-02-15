from json import loads
import logging
import defusedxml.ElementTree as etree

from cryptography.fernet import Fernet
from requests import Session
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, HTTPError, RequestException
from requests.packages.urllib3.exceptions import MaxRetryError
from requests.packages.urllib3.util.retry import Retry
from sdc.rabbit.exceptions import RetryableError, QuarantinableError
from structlog import wrap_logger

from app import receipt
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
        except Exception as e:
            self.logger.error("Exception decrypting message", exception=e)
            raise DecryptError("Failed to decrypt")

        # Validate
        decrypted_json = loads(message)
        self._validate(decrypted_json)

        try:
            case_id = decrypted_json['case_id']
            logger.info("RM submission received {}".format(case_id))
            self._send_rm_receipt(decrypted_json, case_id)
        except KeyError:
            logger.info("RRM Submission received")
            xml = self._encode(decrypted_json)
            self._send_receipt(decrypted_json, xml)
            self.logger = self.logger.unbind("tx_id")

            return

    def _check_namespace_error(self, response):
        """Takes a response from rrm receipt endpoint and examines the xml
        to identify whether a RetryableError or QuarantinableError should
        be raised"""
        namespaces = {'error': 'http://ns.ons.gov.uk/namespaces/resources/error'}
        tree = etree.fromstring(response.content)
        element = tree.find('error:message', namespaces).text
        elements = element.split('-')

        if elements[0] == '1009':
            stat_unit_id = elements[-1].split('statistical_unit_id: ')[-1].split()[0]
            collection_exercise_sid = elements[-1].split(
                'collection_exercise_sid: ')[-1].split()[0]

            self.logger.error("Receipt rejected by RRM endpoint",
                              msg="No records were found on the man_ce_sample_map table",
                              error=1009,
                              stat_unit_id=stat_unit_id,
                              collection_exercise_sid=collection_exercise_sid)
            raise QuarantinableError
        else:
            self.logger.error("Bad response from RRM endpoint")
            raise RetryableError

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

    def _send_rm_receipt(self, decrypted, case_id):
        request_url = settings.RM_SDX_GATEWAY_URL

        try:
            r = self.session.post(request_url, auth=settings.BASIC_AUTH, json={'caseId': case_id})
        except MaxRetryError:
            logger.error("Max retries exceeded (5)",
                         request_url=request_url,
                         case_id=case_id)
            raise RetryableError

        if r.status_code == 200 or r.status_code == 201:
            logger.info("RM sdx gateway receipt creation was a success",
                        request_url=request_url,
                        case_id=case_id)
            return

        elif 400 <= r.status_code < 500:
            logger.error("RM sdx gateway returned client error, unable to receipt",
                         request_url=request_url,
                         status=r.status_code,
                         case_id=case_id)

    def _send_receipt(self, decrypted, xml):
        endpoint = receipt.get_receipt_endpoint(decrypted)
        if endpoint is None:
            logger.info("Unable to determine delivery endpoint from message")
            raise QuarantinableError

        headers = receipt.get_receipt_headers()
        auth = (settings.RECEIPT_USER, settings.RECEIPT_PASS)

        self.logger = self.logger.bind(request_url=endpoint)

        try:
            self.logger.info("Calling external receipting service", service="External receipt")
            response = self.session.post(
                endpoint, data=xml, headers=headers, verify=False, auth=auth)
            self.logger = self.logger.bind(status=response.status_code)

            try:
                response.raise_for_status()
                namespace = {'receipt': 'http://ns.ons.gov.uk/namespaces/resources/receipt'}
                tree = etree.fromstring(xml)
                respondent_id = tree.find('receipt:respondent_id', namespace).text
                if respondent_id is None:
                    self.logger.info("Sent receipt, unable to retrieve respondent id")
                else:
                    self.logger.info("Sent receipt for ", respondent_id=respondent_id)
                return response
            except HTTPError:
                if response.status_code == 400:
                    self.logger.error("Receipt rejected by RRM endpoint")
                    raise QuarantinableError
                elif response.status_code == 404:
                    self._check_namespace_error(response)
                else:
                    self.logger.error("Bad response from RRM endpoint")
                    raise RetryableError
            finally:
                self.logger = self.logger.unbind('status')

        except MaxRetryError:
            msg = "Max retries exceeded. Attempting to send to RRM endpoint"
            self.logger.error(msg, retries=self._retries)
            raise RetryableError
        except ConnectionError:
            self.logger.error("Connection error occured. Retrying")
            raise RetryableError
        except RequestException:
            self.logger.error("Unknown exception occured")
            raise RetryableError
        finally:
            self.logger.unbind('request_url')
