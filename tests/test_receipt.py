import json
import logging
import unittest

import responses
from requests.packages.urllib3 import HTTPConnectionPool
from requests.packages.urllib3.exceptions import MaxRetryError
from sdc.rabbit.exceptions import RetryableError

from app import settings
from app import receipt
from tests.test_data import test_data

logging.disable(logging.CRITICAL)


def get_file_as_string(filename):
    f = open(filename)
    contents = f.read()
    f.close()
    return contents.rstrip("\n")


class TestReceipt(unittest.TestCase):
    def test_get_statistical_unit_id_no_ru_ref(self):
        statistical_unit_id = receipt.get_statistical_unit_id('')
        self.assertEqual(statistical_unit_id, '')

    def test_get_statistical_unit_id_11_character_ru_ref(self):
        ru_ref = '12345678901'
        statistical_unit_id = receipt.get_statistical_unit_id(ru_ref)
        self.assertEqual(statistical_unit_id, ru_ref)

    def test_get_statistical_unit_id_12_character_ru_ref_ending_alpha(self):
        ru_ref = '12345678901A'
        statistical_unit_id = receipt.get_statistical_unit_id(ru_ref)
        self.assertEqual(statistical_unit_id, '12345678901')

    def test_get_statistical_unit_id_12_character_ru_ref_ending_non_alpha(self):
        ru_ref = '123456789012'
        statistical_unit_id = receipt.get_statistical_unit_id(ru_ref)
        self.assertEqual(statistical_unit_id, '123456789012')

    def test_get_statistical_unit_id_14_character_ru_ref(self):
        ru_ref = '12345678901234'
        statistical_unit_id = receipt.get_statistical_unit_id(ru_ref)
        self.assertEqual(statistical_unit_id, ru_ref)

    def test_receipt_endpoint_valid_json(self):
        decrypted_json = json.loads(test_data['valid'])
        endpoint = receipt.get_receipt_endpoint(decrypted_json)
        expected = "http://sdx-mock-receipt:5000/reportingunits/12345678901/collectionexercises/hfjdskf/receipts"

        self.assertEqual(endpoint, expected)

    def test_receipt_endpoint_invalid_json(self):
        decrypted_json = json.loads(test_data['invalid'])
        endpoint = receipt.get_receipt_endpoint(decrypted_json)

        self.assertEqual(endpoint, None)

    def test_get_receipt_headers(self):
        headers = receipt.get_receipt_headers()

        self.assertEqual(headers['Content-Type'], "application/vnd.collections+xml")

    def test_render_xml_valid_json_txid(self):
        decrypted_json = json.loads(test_data['valid'])
        output_xml = receipt.get_receipt_xml(decrypted_json)
        expected_xml = get_file_as_string("./tests/xml/receipt_txid.xml")

        self.assertEqual(output_xml, expected_xml)

    def test_render_xml_valid_json_no_txid(self):
        decrypted_json = json.loads(test_data['valid'])
        del decrypted_json['tx_id']

        output_xml = receipt.get_receipt_xml(decrypted_json)
        expected_xml = get_file_as_string("./tests/xml/receipt_no_txid.xml")

        self.assertEqual(output_xml, expected_xml)


class TestRMReceipt(unittest.TestCase):

    @responses.activate
    def test_send_receipt_201(self):
        responses.add(responses.POST, settings.RM_SDX_GATEWAY_URL,
                      json={'status': 'ok'}, status=201)
        self.assertIsNone(self.consumer._send_receipt(
            case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", tx_id=None))
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_send_receipt_400(self):
        responses.add(responses.POST, settings.RM_SDX_GATEWAY_URL, json={
                      'status': 'client error'}, status=400)

        with self.assertLogs(level="ERROR") as cm:
            self.consumer._send_receipt(case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", tx_id=None)

        self.assertIn("RM sdx gateway returned client error, unable to receipt", cm[0][0].message)

    @responses.activate
    def test_send_receipt_500(self):
        responses.add(responses.POST, settings.RM_SDX_GATEWAY_URL, json={
                      'status': 'server error'}, status=500)

        with self.assertRaises(RetryableError):
            self.consumer._send_receipt(case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", tx_id=None)

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_send_receipt_maxretryerror(self):
        responses.add(responses.POST, settings.RM_SDX_GATEWAY_URL,
                      body=MaxRetryError(HTTPConnectionPool, settings.RM_SDX_GATEWAY_URL))

        with self.assertRaises(RetryableError):
            with self.assertLogs(level="ERROR") as cm:
                self.consumer._send_receipt(
                    case_id="601c4ee4-83ed-11e7-bb31-be2e44b06b34", tx_id=None)

        self.assertIn("Max retries exceeded (5)", cm[0][0].message)
