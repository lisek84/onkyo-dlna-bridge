#!/usr/bin/env python3
"""HTTP proxy: live LPCM stream from swyh-rs -> DLNA renderer of the receiver.

Legacy DLNA renderers (e.g. Onkyo TX-NR609, Mediabolic DMR) probe the stream with
Range requests before playing and expect file-like answers: Content-Length,
Accept-Ranges, 206 + Content-Range. swyh-rs does not answer like that. This proxy
pretends to be a large file and serves the current live stream for every request.

It never returns an error: while swyh-rs is not running yet (or restarts), it sends
silence and switches to the real stream as soon as it is available. A failed stream
can leave the legacy DMR in a locked state (UPnP 705) until it is power-cycled.
Every request from the receiver is logged.
"""
import http.client
import ipaddress
import os
import re
import socketserver
import time
from http.server import BaseHTTPRequestHandler

LISTEN = int(os.environ.get("PROXY_PORT", "5901"))
# swyh-rs address(es), tried in order (localhost first, the LAN address as a fallback)
UP_HOSTS = [h.strip() for h in os.environ.get("UPSTREAM_HOST", "127.0.0.1").split(",") if h.strip()]
UP_PORT = int(os.environ.get("UPSTREAM_PORT", "5911"))
UP_PATH = os.environ.get("UPSTREAM_PATH", "/stream/swyh.lpcm")
CTYPE = "audio/L16;rate=44100;channels=2"
# ~3 h of LPCM 44.1k/16/2; kept below 2^31 so 32-bit parsers in old firmware cope with it
SIZE = int(os.environ.get("PROXY_FAKE_SIZE", "2000000000"))
FEATURES = ("DLNA.ORG_PN=LPCM;DLNA.ORG_OP=01;DLNA.ORG_CI=0;"
            "DLNA.ORG_FLAGS=01700000000000000000000000000000")
SILENCE_CHUNK = 44100          # 0.25 s of 44.1 kHz / 16 bit / stereo
EOF_FLAG = os.environ.get("PROXY_EOF_FLAG", "/tmp/proxy-eof")   # written when a full "file" was served


def parse_allow(spec, renderer):
    """STREAM_ALLOW: empty = everyone; "renderer" = RENDERER_IP; or a comma list of IPs / CIDR subnets."""
    nets = []
    for item in (x.strip() for x in spec.split(",")):
        if not item:
            continue
        if item.lower() == "renderer":
            item = renderer
        try:
            nets.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            print(f"[proxy] ignoring invalid STREAM_ALLOW entry: {item!r}", flush=True)
    return nets


ALLOW = parse_allow(os.environ.get("STREAM_ALLOW", ""), os.environ.get("RENDERER_IP", ""))


def log(msg):
    print(f"[proxy] {time.strftime('%H:%M:%S')} {msg}", flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "onkyo-dlna-bridge"
    sys_version = ""

    def log_message(self, fmt, *args):  # silence the default http.server log
        pass

    def _range(self):
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
        if not m:
            return None
        start = int(m.group(1) or 0)
        end = int(m.group(2)) if m.group(2) else SIZE - 1
        return min(start, SIZE - 1), min(end, SIZE - 1)

    def _headers(self):
        rng = self._range()
        if rng:
            start, end = rng
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{SIZE}")
            length = end - start + 1
        else:
            self.send_response(200)
            length = SIZE
        self.send_header("Content-Type", CTYPE)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("transferMode.dlna.org", "Streaming")
        self.send_header("contentFeatures.dlna.org", FEATURES)
        self.send_header("Connection", "close")
        self.end_headers()
        return length

    def _allowed(self):
        if not ALLOW:
            return True
        try:
            ip = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        if any(ip in n for n in ALLOW) or ip.is_loopback:
            return True
        log(f"{self.client_address[0]} {self.command} {self.path} -> 403 (not in STREAM_ALLOW)")
        self.send_response(403)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()
        return False

    def _log_req(self):
        hdrs = "; ".join(f"{k}: {v}" for k, v in self.headers.items())
        log(f"{self.client_address[0]} {self.command} {self.path} | {hdrs}")

    def do_HEAD(self):
        if not self._allowed():
            return
        self._log_req()
        self._headers()

    def do_GET(self):
        if not self._allowed():
            return
        self._log_req()
        left = self._headers()
        sent = silent = 0
        t0 = time.time()
        up = resp = None
        try:
            while left > 0:
                if resp is None:
                    for host in UP_HOSTS:
                        try:
                            up = http.client.HTTPConnection(host, UP_PORT, timeout=10)
                            up.request("GET", UP_PATH)
                            resp = up.getresponse()
                            if silent:
                                log(f"swyh-rs ready ({host}) after {silent} B of silence")
                            break
                        except OSError:
                            up = resp = None
                    if resp is None:
                        chunk = min(SILENCE_CHUNK, left)    # swyh-rs not up yet: real-time silence
                        self.wfile.write(b"\0" * chunk)
                        left -= chunk
                        sent += chunk
                        silent += chunk
                        time.sleep(0.25)
                        continue
                buf = resp.read1(min(65536, left))
                if not buf:          # swyh-rs ended - keep sending silence until it is back
                    up.close()
                    up = resp = None
                    continue
                self.wfile.write(buf)
                left -= len(buf)
                sent += len(buf)
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass
        finally:
            if up:
                up.close()
        if left == 0 and sent >= SIZE - 1024:
            # the renderer reached the end of the pretended file (~3 h) and will stop -
            # tell the watcher this is not a user Stop
            with open(EOF_FLAG, "w") as f:
                f.write(str(time.time()))
            log("end of the pretended file reached - the stream will be restarted")
        log(f"{self.client_address[0]} done: sent {sent} B (silence {silent} B) in {time.time() - t0:.0f} s")


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    allow = ", ".join(str(n) for n in ALLOW) or "everyone"
    log(f"listening on :{LISTEN} -> {' / '.join(UP_HOSTS)}:{UP_PORT}{UP_PATH} (size {SIZE} B, allowed: {allow})")
    Server(("0.0.0.0", LISTEN), Handler).serve_forever()
