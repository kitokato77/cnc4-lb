import http.server
import socketserver
import threading
import requests
import argparse
import os

GAME_SERVERS = [
    os.getenv('GAME_SERVER_1_URL', 'http://localhost:5001'),
    os.getenv('GAME_SERVER_2_URL', 'http://localhost:5002')
]

server_index = 0
server_lock = threading.Lock()

class LoadBalancerHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def get_next_server(self):
        global server_index
        with server_lock:
            for _ in range(len(GAME_SERVERS)):
                server_url = GAME_SERVERS[server_index]
                server_index = (server_index + 1) % len(GAME_SERVERS)
                try:
                    requests.get(f'{server_url}/game_state', timeout=2)
                    return server_url
                except Exception:
                    continue
            return None

    def do_POST(self):
        server_url = self.get_next_server()
        if server_url is None:
            self._set_headers(503)
            self.wfile.write(b'{"error": "No game server available"}')
            return
        
        url = f'{server_url}{self.path}'
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        
        try:
            resp = requests.post(url, data=body, headers={'Content-Type': 'application/json'}, timeout=5)
            self._set_headers(resp.status_code)
            self.wfile.write(resp.content)
        except Exception:
            self._set_headers(502)
            self.wfile.write(b'{"error": "Game server unavailable"}')

    def do_GET(self):
        server_url = self.get_next_server()
        if server_url is None:
            self._set_headers(503)
            self.wfile.write(b'{"error": "No game server available"}')
            return
        
        url = f'{server_url}{self.path}'
        try:
            resp = requests.get(url, timeout=5)
            self._set_headers(resp.status_code)
            self.wfile.write(resp.content)
        except Exception:
            self._set_headers(502)
            self.wfile.write(b'{"error": "Game server unavailable"}')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    with socketserver.ThreadingTCPServer(("", port), LoadBalancerHandler) as httpd:
        print(f"Load balancer running on port {port}")
        httpd.serve_forever()
