#!/usr/bin/env python3
"""Browser Zombies leaderboard.

Deliberately NOT part of pot.py. That process is the token ledger; it has been
down once already this project over a file-descriptor leak, and a toy
leaderboard has no business sharing a process with the money. This is its own
service, its own database, its own port.

Scores are submitted by the client and are therefore forgeable. That is accepted
-- it is a browser game with no account system. The caps below only stop someone
parking a nonsense number at the top of the table forever.
"""
import json, os, re, sqlite3, time, contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB = os.environ.get("ZSCORES_DB", "/srv/zscores/zscores.db")
PORT = int(os.environ.get("ZSCORES_PORT", "8951"))

MAX_ROUND, MAX_KILLS, MAX_POINTS = 200, 20000, 5_000_000
NAME_OK = re.compile(r"^[A-Za-z0-9 _.\-]{1,16}$")
PER_IP_SECONDS = 5

def connect_raw():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c

@contextlib.contextmanager
def connect():
    """Committed AND closed. `with sqlite3.connect(...)` is a transaction, not a
    resource manager -- that mistake took the ledger down for two hours."""
    c = connect_raw()
    try:
        with c:
            yield c
    finally:
        c.close()

def setup():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS score(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, round INTEGER NOT NULL,
            kills INTEGER NOT NULL, points INTEGER NOT NULL,
            map TEXT, ts INTEGER NOT NULL, ip TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS score_rank ON score(round DESC, points DESC, ts ASC)")

def top(limit=25):
    with connect() as c:
        rows = c.execute(
            "SELECT name,round,kills,points,ts FROM score "
            "ORDER BY round DESC, points DESC, ts ASC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return (fwd.split(",")[0].strip() or self.client_address[0])[:64]

    def do_GET(self):
        if self.path.split("?")[0] == "/zscores":
            try:
                n = int(self.path.split("limit=")[1].split("&")[0]) if "limit=" in self.path else 25
            except ValueError:
                n = 25
            return self._send(200, {"scores": top(max(1, min(n, 100)))})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/zscore":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 2048: raise ValueError("too big")
            d = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})

        name = str(d.get("name", "")).strip()[:16]
        if not NAME_OK.match(name):
            return self._send(400, {"error": "name must be 1-16 letters, digits, space . _ -"})
        try:
            rnd = int(d.get("round", 0)); kills = int(d.get("kills", 0)); pts = int(d.get("points", 0))
        except (TypeError, ValueError):
            return self._send(400, {"error": "bad numbers"})
        if not (1 <= rnd <= MAX_ROUND and 0 <= kills <= MAX_KILLS and 0 <= pts <= MAX_POINTS):
            return self._send(400, {"error": "out of range"})

        ip, now = self._ip(), int(time.time())
        with connect() as c:
            last = c.execute("SELECT ts FROM score WHERE ip=? ORDER BY ts DESC LIMIT 1", (ip,)).fetchone()
            if last and now - last["ts"] < PER_IP_SECONDS:
                return self._send(429, {"error": "slow down"})
            c.execute("INSERT INTO score(name,round,kills,points,map,ts,ip) VALUES(?,?,?,?,?,?,?)",
                      (name, rnd, kills, pts, str(d.get("map", ""))[:32], now, ip))
            rank = c.execute(
                "SELECT COUNT(*)+1 AS r FROM score WHERE round>? OR (round=? AND points>?)",
                (rnd, rnd, pts)).fetchone()["r"]
        return self._send(200, {"ok": True, "rank": rank, "scores": top(25)})

if __name__ == "__main__":
    setup()
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
