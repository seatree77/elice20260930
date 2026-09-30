"""Local development server using the same Supabase API as Vercel."""
import argparse
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from api.registrations import handler

ROOT = Path(__file__).resolve().parent

def load_environment():
    env_file = ROOT / '.env.local'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def create_server(port=8000, store=None):
    class LocalHandler(handler):
        def do_GET(self):
            if urlsplit(self.path).path in ('/', '/index.html'):
                content = (ROOT / 'public' / 'index.html').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif urlsplit(self.path).path == '/api/registrations':
                super().do_GET()
            else:
                self.reply(404, {'message': '페이지를 찾을 수 없습니다.'})
        def do_POST(self):
            if urlsplit(self.path).path == '/api/registrations':
                super().do_POST()
            else:
                self.reply(404, {'message': '페이지를 찾을 수 없습니다.'})
    server = ThreadingHTTPServer(('127.0.0.1', port), LocalHandler)
    server.daemon_threads = True
    server.registration_store = store
    return server

if __name__ == '__main__':
    load_environment()
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    try:
        server = create_server(args.port)
    except OSError as error:
        raise SystemExit(f'Cannot start server: {error}. Try --port 8001.')
    print(f'Open http://127.0.0.1:{server.server_port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
