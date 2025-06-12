"""
Keep-alive server for Replit deployment
This prevents the bot from sleeping due to Replit's timeout policy
"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check HTTP handler"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_HEAD(self):
        """Handle HEAD requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log spam"""
        # Only log errors
        if args[1] != '200':
            logger.info(f"HTTP {args[1]} - {self.path}")

def run_server():
    """Run the keep-alive HTTP server"""
    try:
        server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
        logger.info("Keep-alive server started on port 8000")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Keep-alive server error: {e}")

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    try:
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info("Keep-alive server thread started")
    except Exception as e:
        logger.error(f"Failed to start keep-alive server: {e}")

# Ping function for additional keep-alive (optional)
def ping_self():
    """Ping the health endpoint to keep the service active"""
    import urllib.request
    import urllib.error
    
    while True:
        try:
            time.sleep(300)  # Ping every 5 minutes
            with urllib.request.urlopen('http://localhost:8000/health', timeout=10) as response:
                if response.status == 200:
                    logger.debug("Self-ping successful")
        except urllib.error.URLError:
            logger.warning("Self-ping failed - server may be down")
        except Exception as e:
            logger.error(f"Self-ping error: {e}")

if __name__ == "__main__":
    # Run standalone for testing
    keep_alive()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keep-alive server stopped")
