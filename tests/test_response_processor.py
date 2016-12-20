import base64
import logging
import os
import unittest

from app.response_processor import ResponseProcessor
from tests.test_data import valid_decrypted, invalid_decrypted

from structlog import wrap_logger

logger = wrap_logger(logging.getLogger(__name__))


class TestResponseProcessorSettings(unittest.TestCase):

    @unittest.skipIf(
        "SDX_RECEIPT_RRM_SECRET" in os.environ,
        "variables match live environment"
    )
    def test_no_settings_only_env(self):
        try:
            os.environ["SDX_RECEIPT_RRM_SECRET"] = "y" * 44
            self.assertTrue(os.getenv("SDX_RECEIPT_RRM_SECRET"))
            rv = ResponseProcessor.options()
            self.assertEqual({"secret": b"y" * 44}, rv)
        finally:
            del os.environ["SDX_RECEIPT_RRM_SECRET"]

    def test_no_settings(self):
        rv = ResponseProcessor.options()
        self.assertEqual({}, rv)


class DecryptionTests(unittest.TestCase):

    def test_encrypt_bytes_message(self):
        secret = base64.b64encode(b"x" * 32)
        message = "Test string".encode("utf-8")
        rv = ResponseProcessor.encrypt(message, secret=secret)
        self.assertIsInstance(rv, bytes)
        self.assertIsInstance(rv.decode("ascii"), str)
        self.assertIsInstance(base64.urlsafe_b64decode(rv.decode("ascii")), bytes)

    def test_encrypt_string_message(self):
        secret = base64.b64encode(b"x" * 32)
        message = "Test string"
        rv = ResponseProcessor.encrypt(message, secret=secret)
        self.assertIsInstance(rv, bytes)
        self.assertIsInstance(rv.decode("ascii"), str)
        self.assertIsInstance(base64.urlsafe_b64decode(rv.decode("ascii")), bytes)

    def test_roundtrip_bytes_message(self):
        secret = base64.b64encode(b"x" * 32)
        message = "Test string"
        token = ResponseProcessor.encrypt(message.encode("utf-8"), secret=secret)
        rv = ResponseProcessor.decrypt(token, secret=secret)
        self.assertEqual(message, rv)

    def test_roundtrip_string_message(self):
        secret = base64.b64encode(b"x" * 32)
        message = "Test string"
        token = ResponseProcessor.encrypt(message, secret=secret)
        rv = ResponseProcessor.decrypt(token, secret=secret)
        self.assertEqual(message, rv)

    def test_decrypt_with_string_token(self):
        secret = base64.b64encode(b"x" * 32)
        message = "Test string"
        token = ResponseProcessor.encrypt(message.encode("utf-8"), secret=secret)
        rv = ResponseProcessor.decrypt(token.decode("utf-8"), secret=secret)
        self.assertEqual(message, rv)


class TestResponseProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = ResponseProcessor(logger)
        self.processor.skip_receipt = True

    def test_valid_case_ref(self):
        result = self.processor.process(valid_decrypted)
        self.assertTrue(result)

    def test_invalid_case_ref(self):
        result = self.processor.process(invalid_decrypted)
        self.assertFalse(result)
