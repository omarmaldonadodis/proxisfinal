from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

ALLOWED_ORIGINS = frozenset({
    "https://dashboard.wisebetcore.com",  # producción del ERP
    "http://localhost:3000",              # dev del ERP (Vite default port)
    "http://localhost:5173",              # dev del ERP (Vite alternate port)
})


def start_local_api(agent):

    class Handler(BaseHTTPRequestHandler):
        def _send_cors_headers(self):
            origin = self.headers.get("Origin", "")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")

        def do_GET(self):
            try:
                if self.path == "/whoami":
                    self.send_response(200)
                    self._send_cors_headers()
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "computer_id": agent.config.computer_id,
                        "name": agent.config.agent_name,
                    }).encode())
            except (ConnectionAbortedError, BrokenPipeError):
                pass  

        def do_OPTIONS(self):
            try:
                self.send_response(200)
                self._send_cors_headers()
                self.end_headers()
            except (ConnectionAbortedError, BrokenPipeError):
                pass

        def log_message(self, format, *args):
            pass  # silenciar logs en consola del .exe

    def run():
        server = HTTPServer(("127.0.0.1", 50320), Handler)
        server.serve_forever()

    threading.Thread(target=run, daemon=True).start()
