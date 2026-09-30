import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from app import create_server

class LocalPageTests(unittest.TestCase):
    def test_page_and_private_file(self):
        server = create_server(port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(url) as response:
                self.assertIn('행사 참가 신청', response.read().decode())
            for path in ('/.env.local', '/registrations.db', '/cloud_store.py'):
                with self.assertRaises(HTTPError) as error:
                    urlopen(url + path)
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__':
    unittest.main()
