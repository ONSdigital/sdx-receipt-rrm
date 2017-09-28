import logging
import mock
import json
import unittest
import xml.etree.cElementTree as etree

from cryptography.fernet import Fernet, InvalidToken
import responses
from sdc.rabbit.exceptions import QuarantinableError, RetryableError
from structlog import wrap_logger

from app.response_processor import ResponseProcessor
from app.helpers.exceptions import DecryptError
from app import receipt
from app import settings
from tests.test_data import test_secret, test_data

logger = wrap_logger(logging.getLogger(__name__))
processor = ResponseProcessor(logger)
settings.SDX_RECEIPT_RRM_SECRET = test_secret


def encrypt(plain):
    f = Fernet(test_secret)
    return f.encrypt(plain.encode("utf-8"))


class TestResponseProcessor(unittest.TestCase):

    endpoint = 'http://sdx-mock-receipt:5000/' + \
               'reportingunits/12345678901/collectionexercises/hfjdskf/receipts'

    @responses.activate
    def test_with_valid_data(self):
        responses.add(responses.POST, self.endpoint, status=200)
        processor.process(encrypt(test_data['valid']))

    @responses.activate
    def test_with_invalid_data(self):
        responses.add(responses.POST, self.endpoint, status=200)
        for case in ('invalid', 'missing_metadata'):
            with self.assertRaises(QuarantinableError):
                processor.process(encrypt(test_data[case]))

    @responses.activate
    def test_exception_in_process(self):
        responses.add(responses.POST, self.endpoint, status=200)
        with mock.patch('app.response_processor.ResponseProcessor._decrypt', side_effect=Exception):
            with self.assertRaises(DecryptError):
                processor.process(encrypt(test_data['valid']))


class TestDecrypt(unittest.TestCase):

    def test_decrypt_with_bad_token(self):
        with self.assertRaises(InvalidToken):
            processor._decrypt("xbxhsbhxbsahb", test_secret)

    def test_decrypt_with_good_token(self):
        token = encrypt(test_data['valid'])
        plain = processor._decrypt(token, test_secret)
        self.assertEqual(plain, test_data['valid'])


class TestValidate(unittest.TestCase):

    def test_valid_data(self):
        processor._validate(json.loads(test_data['valid']))

    def test_missing_metadata(self):
        with self.assertRaises(QuarantinableError):
            processor._validate(json.loads(test_data['missing_metadata']))


class TestEncode(unittest.TestCase):

    def test_with_invalid_metadata(self):
        with self.assertRaises(QuarantinableError):
            processor._encode({"bad": "thing"})

    def test_with_valid_data(self):
        processor._encode(json.loads(test_data['valid']))


class TestSend(unittest.TestCase):

    endpoint = 'http://sdx-mock-receipt:5000/' + \
               'reportingunits/12345678901/collectionexercises/hfjdskf/receipts'

    def setUp(self):
        self.decrypted = json.loads(test_data['valid'])
        self.xml = processor._encode(self.decrypted)

    @responses.activate
    def test_with_200_response(self):
        responses.add(responses.POST, self.endpoint, status=200)
        processor._send_receipt(self.decrypted, self.xml)

    @responses.activate
    def test_quarantinable_error_if_endpoint_none(self):
        responses.add(responses.POST, self.endpoint, status=200)
        with mock.patch('app.receipt.get_receipt_endpoint', return_value=None):
            with self.assertRaises(QuarantinableError):
                processor._send_receipt(self.decrypted, self.xml)

    @responses.activate
    def test_with_500_response(self):
        responses.add(responses.POST, self.endpoint, status=500)
        with self.assertRaises(RetryableError):
            processor._send_receipt(self.decrypted, self.xml)

    @responses.activate
    def test_with_400_response(self):
        responses.add(responses.POST, self.endpoint, status=400)
        with self.assertRaises(QuarantinableError):
            processor._send_receipt(self.decrypted, self.xml)

    @responses.activate
    def test_with_404_response(self):
        """Test that a 404 response with no 1009 error in the response XML continues
           execution assuming a transient error.
        """
        etree.register_namespace('', "http://ns.ons.gov.uk/namespaces/resources/error")
        file_path = './tests/xml/receipt_404.xml'
        tree = etree.parse(file_path)
        root = tree.getroot()
        tree_as_str = etree.tostring(root, encoding='utf-8')
        endpoint = receipt.get_receipt_endpoint(self.decrypted)

        responses.add(responses.POST, endpoint,
                      body=tree_as_str, status=404,
                      content_type='application/xml')

        with self.assertRaises(RetryableError):
            resp = processor._send_receipt(self.decrypted, self.xml)  # noqa

    @responses.activate
    def test_with_404_1009_response(self):
        """Test that a 404 response with a 1009 error in the response XML raises
           BadMessage error.
        """
        etree.register_namespace('', "http://ns.ons.gov.uk/namespaces/resources/error")
        file_path = './tests/xml/receipt_incorrect_ru_ce.xml'
        tree = etree.parse(file_path)
        root = tree.getroot()
        tree_as_str = etree.tostring(root, encoding='utf-8')
        endpoint = receipt.get_receipt_endpoint(self.decrypted)

        responses.add(responses.POST, endpoint,
                      body=tree_as_str, status=404,
                      content_type='application/xml')

        with self.assertRaises(QuarantinableError):
            resp = processor._send_receipt(self.decrypted, self.xml)  # noqa

        @responses.activate
        def test_network_error(self):
            """Test that a RetryableError is raised when anything goes wrong at the
            network level."""
            responses.add(responses.POST, self.endpoint, body=ConnectionError('error'))
            with self.assertRaises(RetryableError):
                processor._send_receipt(self.decrypted, self.xml)
