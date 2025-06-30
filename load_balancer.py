import http.server
import socketserver
import threading
import requests
import argparse
import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Game servers configuration
GAME_SERVERS = []
if os.getenv('GAME_SERVER_1_URL'):
    GAME_SERVERS.append(os.getenv('GAME_SERVER_1_URL'))
if os.getenv('GAME_SERVER_2_URL'):
    GAME_SERVERS.append(os.getenv('GAME_SERVER_2_URL'))

# Fallback to default if no env vars set
if not GAME_SERVERS:
    GAME_SERVERS = ['http://localhost:5001', 'http://localhost:5002']

logger.info(f"Configured game servers: {GAME_SERVERS}")

server_index = 0
server_lock = threading.Lock()
server_health = {}  # Track server health

class LoadBalancerHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Custom logging to use logger instead of print
        logger.info(f"{self.address_string()} - {format % args}")
    
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        logger.info(f"OPTIONS request for {self.path}")
        self._set_headers(200)

    def health_check_server(self, server_url):
        """Quick health check for a server"""
        try:
            # Use /health endpoint if available, otherwise root endpoint
            health_url = f'{server_url}/health'
            resp = requests.get(health_url, timeout=3)
            if resp.status_code == 200:
                return True
            # Fallback to root endpoint
            resp = requests.get(f'{server_url}/', timeout=3)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {server_url}: {e}")
            return False

    def get_next_server(self):
        """Get next available server with health checking"""
        global server_index
        with server_lock:
            attempts = 0
            while attempts < len(GAME_SERVERS) * 2:  # Try each server twice
                server_url = GAME_SERVERS[server_index]
                server_index = (server_index + 1) % len(GAME_SERVERS)
                attempts += 1
                
                # Check if server is healthy
                if self.health_check_server(server_url):
                    server_health[server_url] = True
                    logger.info(f"Using healthy server: {server_url}")
                    return server_url
                else:
                    server_health[server_url] = False
                    logger.warning(f"Server unhealthy: {server_url}")
            
            logger.error("No healthy servers available")
            return None

    def forward_request(self, method, server_url, path, body=None, headers=None):
        """Forward request to game server with better error handling"""
        url = f'{server_url}{path}'
        logger.info(f"Forwarding {method} {url}")
        
        try:
            if method == 'GET':
                resp = requests.get(url, timeout=10)
            elif method == 'POST':
                request_headers = {'Content-Type': 'application/json'}
                resp = requests.post(url, data=body, headers=request_headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            logger.info(f"Server response: {resp.status_code}")
            return resp
        except requests.exceptions.Timeout:
            logger.error(f"Timeout forwarding to {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {url}")
            raise
        except Exception as e:
            logger.error(f"Error forwarding to {url}: {e}")
            raise

    def do_POST(self):
        logger.info(f"POST request for {self.path}")
        
        # Special endpoint for load balancer health
        if self.path == '/lb_health':
            self._set_headers(200)
            health_status = {
                'status': 'healthy',
                'servers': server_health,
                'available_servers': [url for url, healthy in server_health.items() if healthy]
            }
            self.wfile.write(json.dumps(health_status).encode())
            return
        
        server_url = self.get_next_server()
        if server_url is None:
            logger.error("No server available for POST request")
            self._set_headers(503)
            self.wfile.write(json.dumps({'error': 'No game server available', 'servers_checked': GAME_SERVERS}).encode())
            return
        
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length > 0 else b''
            
            resp = self.forward_request('POST', server_url, self.path, body)
            self._set_headers(resp.status_code)
            self.wfile.write(resp.content)
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout on POST to {server_url}")
            self._set_headers(504)
            self.wfile.write(json.dumps({'error': 'Gateway timeout'}).encode())
        except Exception as e:
            logger.error(f"Exception on POST: {e}")
            self._set_headers(502)
            self.wfile.write(json.dumps({'error': 'Game server unavailable'}).encode())

    def do_GET(self):
        logger.info(f"GET request for {self.path}")
        
        # Special endpoint for load balancer health
        if self.path == '/lb_health':
            self._set_headers(200)
            health_status = {
                'status': 'healthy',
                'servers': server_health,
                'available_servers': [url for url, healthy in server_health.items() if healthy]
            }
            self.wfile.write(json.dumps(health_status).encode())
            return
        
        # Load balancer info endpoint
        if self.path == '/':
            self._set_headers(200)
            info = {
                'service': 'Connect Four Load Balancer',
                'servers': GAME_SERVERS,
                'health': server_health
            }
            self.wfile.write(json.dumps(info).encode())
            return
        
        server_url = self.get_next_server()
        if server_url is None:
            logger.error("No server available for GET request")
            self._set_headers(503)
            self.wfile.write(json.dumps({'error': 'No game server available', 'servers_checked': GAME_SERVERS}).encode())
            return
        
        try:
            resp = self.forward_request('GET', server_url, self.path)
            self._set_headers(resp.status_code)
            self.wfile.write(resp.content)
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout on GET to {server_url}")
            self._set_headers(504)
            self.wfile.write(json.dumps({'error': 'Gateway timeout'}).encode())
        except Exception as e:
            logger.error(f"Exception on GET: {e}")
            self._set_headers(502)
            self.wfile.write(json.dumps({'error': 'Game server unavailable'}).encode())

def periodic_health_check():
    """Periodic health check for all servers"""
    import time
    handler = LoadBalancerHandler(None, None, None)
    
    while True:
        logger.info("Running periodic health check...")
        for server_url in GAME_SERVERS:
            healthy = handler.health_check_server(server_url)
            server_health[server_url] = healthy
            logger.info(f"Server {server_url}: {'healthy' if healthy else 'unhealthy'}")
        time.sleep(30)  # Check every 30 seconds

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    # Start periodic health check in background thread
    health_thread = threading.Thread(target=periodic_health_check, daemon=True)
    health_thread.start()
    
    logger.info(f"Starting load balancer on port {port}")
    logger.info(f"Game servers: {GAME_SERVERS}")
    
    with socketserver.ThreadingTCPServer(("", port), LoadBalancerHandler) as httpd:
        logger.info(f"Load balancer running on port {port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down load balancer")
            httpd.shutdown()
