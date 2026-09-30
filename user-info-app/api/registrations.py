import json
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit
from uuid import UUID

from cloud_store import SupabaseStore, StorageError, RateLimitError

EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+')


class handler(BaseHTTPRequestHandler):
    def reply(self, code, payload):
        content = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if code == 405:
            self.send_header('Allow', 'POST')
        if code == 429:
            self.send_header('Retry-After', '600')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        self.reply(405, {'message': '신청 제출만 지원합니다.'})

    do_PUT = do_GET
    do_PATCH = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            self.reply(403, {'message': '신청 페이지에서 다시 제출해 주세요.'})
            return
        if self.headers.get_content_type() != 'application/json':
            self.reply(415, {'message': 'JSON 형식으로 제출해 주세요.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size > 16384:
                self.reply(413, {'message': '입력 내용이 너무 큽니다.'})
                return
            if size <= 0:
                raise ValueError()
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()
            fields = ('name', 'email', 'session', 'request_id')
            if not all(isinstance(data.get(field), str) for field in fields):
                raise ValueError()
            data = {field: data[field].strip() for field in fields}
            if not 1 <= len(data['name']) <= 100 or len(data['email']) > 254 or not EMAIL.fullmatch(data['email']) or data['session'] not in ('1', '2', '3'):
                raise ValueError()
            if str(UUID(data['request_id'])) != data['request_id']:
                raise ValueError()
        except (ValueError, UnicodeDecodeError):
            self.reply(400, {'message': '이름, 올바른 이메일, 참가 회차를 확인해 주세요.'})
            return
        try:
            store = getattr(self.server, 'registration_store', None) or SupabaseStore()
            # Vercel overwrites x-vercel-forwarded-for. Locally use the socket peer.
            client_ip = self.client_address[0]
            if os.environ.get('VERCEL') == '1':
                client_ip = self.headers.get('x-vercel-forwarded-for', client_ip).split(',')[0].strip()
            result = store(data, client_ip)
        except RateLimitError:
            self.reply(429, {'message': '신청이 너무 많습니다. 10분 후 다시 시도해 주세요.'})
            return
        except StorageError:
            self.reply(503, {'message': '저장하지 못했습니다. 입력 내용을 유지한 채 잠시 후 다시 신청해 주세요.'})
            return
        self.reply(201, {'id': result, 'message': '신청이 완료되었습니다.'})
