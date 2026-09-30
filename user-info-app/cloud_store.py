"""Server-only Supabase REST access; no third-party Python dependencies."""
import hashlib
import hmac
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class StorageError(Exception):
    pass


class RateLimitError(StorageError):
    pass


class SupabaseStore:
    def __init__(self, url=None, key=None):
        self.url = (url or os.environ.get('SUPABASE_URL', '')).rstrip('/')
        self.key = key or os.environ.get('SUPABASE_SECRET_KEY', '')
        if not self.url.startswith('https://') or not self.key:
            raise StorageError('Missing server configuration')

    def __call__(self, data, client_ip):
        fingerprint = hmac.new(self.key.encode(), client_ip.encode(), hashlib.sha256).hexdigest()
        payload = {f'p_{field}': data[field] for field in ('name', 'email', 'session', 'request_id')}
        payload['p_fingerprint'] = fingerprint
        headers = {'apikey': self.key, 'Content-Type': 'application/json'}
        # Legacy service_role JWTs require Authorization; modern secret keys do not.
        if self.key.startswith('eyJ'):
            headers['Authorization'] = 'Bearer ' + self.key
        request = Request(self.url + '/rest/v1/rpc/submit_workshop_registration',
                          json.dumps(payload).encode('utf-8'), headers, method='POST')
        try:
            with urlopen(request, timeout=8) as response:
                result = json.load(response)
            if result != data['request_id']:
                raise StorageError('Unexpected storage response')
            return result
        except HTTPError as error:
            detail = error.read(8192)
            if b'registration_rate_limit' in detail:
                raise RateLimitError() from None
            raise StorageError('Database request failed') from None
        except (URLError, TimeoutError, OSError, ValueError) as error:
            raise StorageError('Database unavailable') from None
