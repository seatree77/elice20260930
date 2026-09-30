import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from unittest.mock import patch
from uuid import uuid4

from api.registrations import handler
from cloud_store import SupabaseStore, StorageError, RateLimitError


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.saved = []
        self.store = lambda data, fingerprint: self.saved.append(data) or data['request_id']
        class TestHandler(handler):
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), TestHandler)
        self.server.registration_store = lambda data, fingerprint: self.store(data, fingerprint)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}/api/registrations'
        self.data = {'name': ' 테스트 ', 'email': 'test@example.com', 'session': '2', 'request_id': str(uuid4())}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, data=None, raw=None, headers=None):
        payload = raw if raw is not None else json.dumps(data or self.data).encode()
        request = Request(self.url, payload, headers or {'Content-Type': 'application/json'})
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_valid_submission(self):
        code, result = self.post()
        self.assertEqual(code, 201)
        self.assertEqual(result['id'], self.data['request_id'])
        self.assertEqual(self.saved[0]['name'], '테스트')

    def test_invalid_inputs_never_reach_storage(self):
        for field, value in [('name', ' '), ('name', []), ('email', 'bad'),
                             ('session', '4'), ('request_id', 'bad')]:
            self.assertEqual(self.post({**self.data, field: value})[0], 400)
        self.assertEqual(self.post(raw=b'{bad')[0], 400)
        self.assertEqual(self.post(raw=b'[]')[0], 400)
        self.assertEqual(self.post(raw=b'x' * 16385)[0], 413)
        self.assertEqual(self.post(headers={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.saved, [])

    def test_storage_failure_and_rate_limit(self):
        def fail(*args):
            raise StorageError('secret internal error')
        self.store = fail
        code, response = self.post()
        self.assertEqual(code, 503)
        self.assertNotIn('secret', str(response))
        def limit(*args):
            raise RateLimitError()
        self.store = limit
        self.assertEqual(self.post()[0], 429)

    def test_cross_origin_rejected(self):
        headers = {'Content-Type': 'application/json', 'Origin': 'https://other.example'}
        self.assertEqual(self.post(headers=headers)[0], 403)
        self.assertEqual(self.saved, [])

    def test_read_not_allowed(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url)
        self.assertEqual(error.exception.code, 405)

    def test_supabase_request_and_failure(self):
        response = io.BytesIO(json.dumps(self.data['request_id']).encode())
        with patch('cloud_store.urlopen', return_value=response) as send:
            store = SupabaseStore('https://example.supabase.co', 'server-secret')
            self.assertEqual(store(self.data, '127.0.0.1'), self.data['request_id'])
            request = send.call_args.args[0]
            self.assertTrue(request.full_url.endswith('/rest/v1/rpc/submit_workshop_registration'))
            body = json.loads(request.data)
            self.assertNotIn('127.0.0.1', body['p_fingerprint'])
            self.assertEqual(body['p_session'], '2')
        with patch('cloud_store.urlopen', side_effect=URLError('offline')):
            with self.assertRaises(StorageError):
                store(self.data, '127.0.0.1')


if __name__ == '__main__':
    unittest.main()
