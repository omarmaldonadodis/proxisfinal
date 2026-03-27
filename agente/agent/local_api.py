from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

def start_local_api(agent):

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/whoami":
                self.send_response(200)

                # ✅ CORS HEADERS (ESTO SOLUCIONA TODO)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")

                self.send_header("Content-type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "computer_id": agent.config.computer_id,
                    "name": agent.config.agent_name,
                }).encode())

        # 🔥 IMPORTANTE: manejar preflight (OPTIONS)
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

    def run():
        server = HTTPServer(("127.0.0.1", 50320), Handler)
        server.serve_forever()

    threading.Thread(target=run, daemon=True).start()