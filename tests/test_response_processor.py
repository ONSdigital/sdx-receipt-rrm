import unittest
import mock
import json
import xml.etree.cElementTree as etree

from cryptography.fernet import Fernet, InvalidToken
import responses
from app.response_processor import ResponseProcessor
from app.helpers.exceptions import BadMessageError, RetryableError
from tests.test_data import test_secret, test_data
from app import receipt
from app import settings

import logging
from structlog import wrap_logger

logger = wrap_logger(logging.getLogger(__name__))
processor = ResponseProcessor(logger)
settings.SDX_RECEIPT_RRM_SECRET = test_secret


def encrypt(plain):
    f = Fernet(test_secret)
    return f.encrypt(plain.encode("utf-8"))


class MockResponse:
    def __init__(self, status, content=None):
        self.status_code = status
        self.url = ""
        self.content = ""


class TestResponseProcessor(unittest.TestCase):

    def test_with_valid_data(self):
        with mock.patch('app.response_processor.session.post') as session_mock:
            session_mock.return_value = MockResponse(status=200)
            processor.process(encrypt(test_data['valid']))

    def test_with_invalid_data(self):
        with mock.patch('app.response_processor.session.post') as session_mock:
            session_mock.return_value = MockResponse(status=200)
            for case in ('invalid', 'missing_metadata'):
                with self.assertRaises(BadMessageError):
                    processor.process(encrypt(test_data[case]))


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
        with self.assertRaises(BadMessageError):
            processor._validate(json.loads(test_data['missing_metadata']))


class TestEncode(unittest.TestCase):

    def test_with_invalid_metadata(self):
        with self.assertRaises(BadMessageError):
            processor._encode({"bad": "thing"})

    def test_with_valid_data(self):
        processor._encode(json.loads(test_data['valid']))


class TestSend(unittest.TestCase):

    def setUp(self):
        self.decrypted = json.loads(test_data['valid'])
        self.xml = processor._encode(self.decrypted)

    def test_with_200_response(self):
        with mock.patch('app.response_processor.session.post') as session_mock:
            session_mock.return_value = MockResponse(status=200)
            processor._send_receipt(self.decrypted, self.xml)

    def test_with_500_response(self):
        with self.assertRaises(RetryableError):
            with mock.patch('app.response_processor.session.post') as session_mock:
                session_mock.return_value = MockResponse(status=500)
                processor._send_receipt(self.decrypted, self.xml)

    def test_with_400_response(self):
        with self.assertRaises(BadMessageError):
            with mock.patch('app.response_processor.session.post') as session_mock:
                session_mock.return_value = MockResponse(status=400)
                processor._send_receipt(self.decrypted, self.xml)

    @responses.activate
    def test_with_404_response(self):
        """Test that a 404 response with no 1009 error in the response XMl continues
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
            resp = processor._send_receipt(self.decrypted, self.xml)

    @responses.activate
    def test_with_404_1009_response(self):
        """Test that a 404 response with a 1009 error in the response XMl raises
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

        with self.assertRaises(BadMessageError):
            resp = processor._send_receipt(self.decrypted, self.xml)

"""
    def test_with_404_response_ru_ce_incorrect(self):
        file_path = './tests/xml/receipt_incorrect_ru_ce.xml'
        tree = etree.parse(file_path)
        root = tree.getroot()
        tree_as_str = etree.tostring(root, encoding='utf-8')
        endpoint = receipt.get_receipt_endpoint(self.decrypted)
        processor._send_receipt(self.decrypted, self.xml)
"""
