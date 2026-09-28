"""The POC as a plain web page: pick any doc from a dropdown, ask a question, see every step.

    uv run poc/server.py                 # real Jev API when JEV_API_KEY is set, else the keyword mock
    uv run poc/server.py --mock          # force the mock
    uv run poc/server.py --port 9000

Standard library HTTP server; the only dependency is the jev SDK via poc.py.

    GET  /            the page (poc/web/index.html)
    GET  /api/docs    every doc, parsed, plus mode and example questions
    POST /api/route   {"question": "..."} -> the route with every step and its probabilities
"""
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).parent))
import poc  # noqa: E402

WEB = Path(__file__).parent / "web"
QUESTIONS = Path(__file__).parent / "questions.jsonl"


def examples():
    if not QUESTIONS.exists():
        return poc.DEMO
    lines = [l for l in QUESTIONS.read_text().splitlines() if l.strip() and not l.startswith("#")]
    return [json.loads(l)["question"] for l in lines]


class Handler(BaseHTTPRequestHandler):
    jev = None
    mock = False

    def do_GET(self):
        path = urlsplit(self.path).path  # ignore ?q=... which the page reads itself
        if path in ("/", "/index.html"):
            return self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/docs":
            tree = poc.read_docs()  # re-read every time so edits to the docs show up on reload
            docs = [{"ref": "%s/%s" % (d, name), "domain": d, "name": name, **f}
                    for d, dom in tree.items() for name, f in dom["files"].items()]
            domains = {d: dom["about"] for d, dom in tree.items()}
            mode = "mock" if self.mock else "live"
            return self._json(200, {"mode": mode, "domains": domains, "docs": docs, "examples": examples(),
                                    "pricing": poc.pricing()})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/route":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("content-length") or 0)
            question = (json.loads(self.rfile.read(length) or b"{}").get("question") or "").strip()
            if not question:
                return self._json(400, {"error": "ask a question"})
            self._json(200, poc.route(self.jev, poc.read_docs(), question))
        except Exception as exc:  # show the failure on the page rather than a dropped connection
            traceback.print_exc()
            self._json(500, {"error": "%s: %s" % (type(exc).__name__, exc)})

    def _json(self, status, payload):
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))


def main(argv):
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8765
    Handler.mock = poc.use_mock("--mock" in argv)
    Handler.jev = poc.client(Handler.mock)  # one client, shared: the SDK client is thread-safe
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("jev docs POC on http://127.0.0.1:%d  (%s)" % (port, "keyword mock: set JEV_API_KEY for the real API" if Handler.mock else "live Jev API"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])
