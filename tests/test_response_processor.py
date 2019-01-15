import mock
import json
import unittest

from cryptography.fernet import Fernet, InvalidToken
import responses
from requests.packages.urllib3 import HTTPConnectionPool
from requests.packages.urllib3.exceptions import MaxRetryError
from sdc.rabbit.exceptions import QuarantinableError, RetryableError

from app.response_processor import ResponseProcessor
from app.helpers.exceptions import DecryptError
from app import settings
from tests.test_data import test_secret, test_data

processor = ResponseProcessor()
settings.SDX_RECEIPT_RRM_SECRET = test_secret


def encrypt(plain):
    f = Fernet(test_secret)
    return f.encrypt(plain.encode("utf-8"))


class TestResponseProcessor(unittest.TestCase):

    endpoint = 'http://sdx-mock-receipt:5000/receipts'

    @responses.activate
    def test_with_invalid_data(self):
        responses.add(responses.POST, self.endpoint, status=200)
        for case in ('invalid', 'missing_metadata'):
            with self.assertRaises(QuarantinableError):
                processor.process(encrypt(test_data[case]))

    @responses.activate
    def test_missing_tx_id(self):
        responses.add(responses.POST, self.endpoint, status=200)
        with self.assertRaises(QuarantinableError):
            processor.process(encrypt(test_data['missing_tx_id']))

    @responses.activate
    def test_missing_case_id(self):
        responses.add(responses.POST, self.endpoint, status=200)
        with self.assertRaises(QuarantinableError):
            processor.process(encrypt(test_data['missing_case_id']))


class TestDecrypt(unittest.TestCase):
    def test_decrypt_with_bad_token(self):
        with self.assertRaises(InvalidToken):
            processor._decrypt("xbxhsbhxbsahb", test_secret)

    def test_decrypt_with_good_token(self):
        token = encrypt(test_data['valid'])
        plain = processor._decrypt(token, test_secret)
        self.assertEqual(plain, test_data['valid'])

    def test_exception_in_process(self):
        with mock.patch(
                'app.response_processor.ResponseProcessor._decrypt',
                side_effect=Exception):
            with self.assertRaises(DecryptError):
                processor.process(encrypt(test_data['valid']))


class TestValidate(unittest.TestCase):
    def test_valid_data(self):
        processor._validate(json.loads(test_data['valid']))

    def test_missing_metadata(self):
        with self.assertRaises(QuarantinableError):
            processor._validate(json.loads(test_data['missing_metadata']))


class TestRMReceipt(unittest.TestCase):
    def setUp(self):
        self.decrypted_rm = json.loads(test_data['valid'])

    @responses.activate
    def test_send_rm_receipt_201(self):
        responses.add(
            responses.POST,
            settings.RM_SDX_GATEWAY_URL,
            json={'status': 'ok'},
            status=201)

        self.assertIsNone(
            processor._send_rm_receipt(case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", user_id="27d38da4-02cf-44e4-8866-3db1be726030"))

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_send_rm_eceipt_400(self):
        responses.add(
            responses.POST,
            settings.RM_SDX_GATEWAY_URL,
            json={'status': 'client error'},
            status=400)

        with self.assertRaises(QuarantinableError):
            processor._send_rm_receipt(case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", user_id="27d38da4-02cf-44e4-8866-3db1be726030")

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_send_rm_receipt_500(self):
        responses.add(
            responses.POST,
            settings.RM_SDX_GATEWAY_URL,
            json={'status': 'server error'},
            status=500)

        with self.assertRaises(RetryableError):
            processor._send_rm_receipt(case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", user_id="27d38da4-02cf-44e4-8866-3db1be726030")

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_send_rm_receipt_maxretryerror(self):
        responses.add(
            responses.POST,
            settings.RM_SDX_GATEWAY_URL,
            body=MaxRetryError(HTTPConnectionPool,
                               settings.RM_SDX_GATEWAY_URL))

        with self.assertRaises(RetryableError):
            with self.assertLogs(level="ERROR") as cm:
                processor._send_rm_receipt(case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", user_id="27d38da4-02cf-44e4-8866-3db1be726030")

            self.assertIn("Max retries exceeded (5)", cm.output)

    @responses.activate
    def test_rm_routing_on_case_id(self):
        responses.add(
            responses.POST,
            settings.RM_SDX_GATEWAY_URL,
            json={'status': 'ok'},
            status=201)
        processor.process(encrypt(test_data['valid']))

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, settings.RM_SDX_GATEWAY_URL)
        self.assertEqual(responses.calls[0].response.text, '{"status": "ok"}')
