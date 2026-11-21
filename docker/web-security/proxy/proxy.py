import os
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8080
UPSTREAM_HOST = os.environ["NEXIS_UPSTREAM_HOST"]
UPSTREAM_PORT = 8080
UPSTREAM_TIMEOUT = 5
MAX_RESPONSE_SIZE = 64 * 1024
ALLOWED_PATHS = {"/", "/robots.txt", "/training-hint"}


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "NEXISProxy"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path not in ALLOWED_PATHS:
            self.send_text(404, "Not found\n")
            return

        connection = HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=UPSTREAM_TIMEOUT)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            data = response.read(MAX_RESPONSE_SIZE + 1)
            if len(data) > MAX_RESPONSE_SIZE:
                self.send_text(502, "Response too large\n")
                return
            content_type = response.getheader("Content-Type", "text/plain; charset=utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        except (OSError, HTTPException) as exc:
            self.log_error("Upstream error: %s", type(exc).__name__)
            self.send_text(502, "Bad Gateway\n")
        finally:
            connection.close()

    def do_POST(self):
        self.send_text(405, "Method Not Allowed\n")

    def do_PUT(self):
        self.send_text(405, "Method Not Allowed\n")

    def do_DELETE(self):
        self.send_text(405, "Method Not Allowed\n")

    def do_PATCH(self):
        self.send_text(405, "Method Not Allowed\n")

    def do_HEAD(self):
        self.send_text(405, "Method Not Allowed\n")

    def do_OPTIONS(self):
        self.send_text(405, "Method Not Allowed\n")

    def do_CONNECT(self):
        self.send_text(405, "Method Not Allowed\n")

    def send_text(self, status, message):
        data = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), ProxyHandler)
    print(f"NEXIS Proxy listening on {HOST}:{PORT}, upstream {UPSTREAM_HOST}:{UPSTREAM_PORT}", flush=True)
    server.serve_forever()