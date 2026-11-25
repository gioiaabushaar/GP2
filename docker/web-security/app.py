from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

HOST = "0.0.0.0"
PORT = 8080

HOME_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>NEXIS Web Security Lab</title>
</head>
<body>
  <h1>Welcome to NEXIS</h1>
  <h2>Web Security Training Lab</h2>
  <p>Challenge: Explore this website.</p>
  <p>Can you discover the hidden training flag?</p>
  <p>Use your browser or HTTP tools.</p>
</body>
</html>
"""

ROBOTS_TXT = "User-agent: *\nDisallow: /training-hint\n"

HINT_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Training Hint</title></head>
<body>
  <p>Training flag: NEXIS{web_recon_basics}</p>
</body>
</html>
"""

ROUTES = {
    "/": (HOME_PAGE, "text/html; charset=utf-8"),
    "/robots.txt": (ROBOTS_TXT, "text/plain; charset=utf-8"),
    "/training-hint": (HINT_PAGE, "text/html; charset=utf-8"),
    "/health": ("ok\n", "text/plain; charset=utf-8"),
}


class WebLabHandler(BaseHTTPRequestHandler):
    server_version = "NEXISWebLab"

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ROUTES:
            body, content_type = ROUTES[path]
            self._send(200, body, content_type)
        else:
            self._send(404, "Not found\n", "text/plain; charset=utf-8")

    def _send(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), WebLabHandler)
    print(f"NEXIS Web Security Lab listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()