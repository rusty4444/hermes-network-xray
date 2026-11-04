"""Controlled, loopback-only HTTP fixture for the documented two-machine demo."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "NetworkXrayDemo/0.1"
    sys_version = ""

    def do_HEAD(self):
        code = 200 if self.path == "/health" else 404
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self.do_HEAD()

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18764)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose an unprivileged port")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    print(f"Controlled demo service: http://127.0.0.1:{args.port}/health", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
