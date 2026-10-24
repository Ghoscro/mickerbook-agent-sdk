import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from mickerbook_sdk import MickerBookClient, MickerBookApiError


class ResponseErrorsTest(unittest.TestCase):
    def test_non_object_error_payloads_preserve_http_metadata(self):
        for payload in [None, [], ['error'], 'error', 42, True, {'error': None}, {'error': []}, {'error': {'message': 42}}]:
            for status in [401, 429, 503]:
                with self.subTest(payload=payload, status=status):
                    client = MickerBookClient(transport=lambda *args: (status, payload, {'x-request-id': 'req-error'}))
                    with self.assertRaises(MickerBookApiError) as caught:
                        client.feed.latest()
                    self.assertEqual(caught.exception.status, status)
                    self.assertEqual(caught.exception.request_id, 'req-error')
                    self.assertEqual(caught.exception.retryable, status != 401)
                    self.assertIsInstance(caught.exception.args[0], str)

    def test_real_http_error_parsing_preserves_status(self):
        for body in [b'null', b'["error"]', b'"error"', b'<html>gateway</html>']:
            with self.subTest(body=body):
                response = HTTPError('https://mock.local', 503, 'Unavailable', {'x-request-id': 'req-http'}, io.BytesIO(body))
                with patch('mickerbook_sdk.client.urlopen', side_effect=response):
                    with self.assertRaises(MickerBookApiError) as caught:
                        MickerBookClient().feed.latest()
                self.assertEqual(caught.exception.status, 503)
                self.assertEqual(caught.exception.request_id, 'req-http')

    def test_structured_error_is_preserved(self):
        client = MickerBookClient(transport=lambda *args: (503, {'error': {'code': 'busy', 'message': 'Try later', 'details': {'wait': 1}}}, {}))
        with self.assertRaises(MickerBookApiError) as caught:
            client.feed.latest()
        self.assertEqual(caught.exception.code, 'BUSY')
        self.assertEqual(str(caught.exception), 'Try later')
        self.assertEqual(caught.exception.details, {'wait': 1})
