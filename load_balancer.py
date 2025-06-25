import http.server
import socketserver
import threading
import requests
import urllib.parse

GAME_SERVERS = [5001, 5002]
server_index = 0
server_lock = threading.Lock()

class LoadBalancerHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def get_next_server(self):
        global server_index
        with server_lock:
            for _ in range(len(GAME_SERVERS)):
                port = GAME_SERVERS[server_index]
                server_index = (server_index + 1) % len(GAME_SERVERS)
                try:
                    requests.get(f'http://localhost:{port}/game_state', timeout=0.5)
                    return port
                except Exception:
                    continue
            return None

    def do_POST(self):
        port = self.get_next_server()
        if port is None:
            self._set_headers(503)
            self.wfile.write(b'{"error": "No game server available"}')
            return
        url = f'http://localhost:{port}{self.path}'
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            resp = requests.post(url, data=body, headers={'Content-Type': 'application/json'}, timeout=3)
            self._set_headers(resp.status_code)
            self.wfile.write(resp.content)
        except Exception:
            self._set_headers(502)
            self.wfile.write(b'{"error": "Game server unavailable"}')

    def do_GET(self):
        port = self.get_next_server()
        if port is None:
            self._set_headers(503)
            self.wfile.write(b'{"error": "No game server available"}')
            return
        url = f'http://localhost:{port}{self.path}'
        try:
            resp = requests.get(url, timeout=3)
            self._set_headers(resp.status_code)
            self.wfile.write(resp.content)
        except Exception:
            self._set_headers(502)
            self.wfile.write(b'{"error": "Game server unavailable"}')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    with socketserver.ThreadingTCPServer(("", args.port), LoadBalancerHandler) as httpd:
        print(f"Load balancer running on port {args.port}")
        httpd.serve_forever()
