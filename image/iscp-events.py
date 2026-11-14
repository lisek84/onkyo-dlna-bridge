#!/usr/bin/env python3
"""Persistent eISCP connection to the receiver (Onkyo/Integra/Pioneer, TCP 60128).

Logs relevant events and writes marker files read by the watcher in entrypoint.sh:
  /tmp/iscp-net  - time of the last NET button press (SLI2B, or NLTF3... = NET top menu)
  /tmp/iscp-off  - time of the last power-off transition (PWR01 -> PWR00)
In DLNA renderer mode the receiver reports only these; Play/Pause/Next/FF on the
remote are handled internally and are not reported over the network.
"""
import os
import socket
import struct
import time

IP = os.environ["RENDERER_IP"]
NET_FLAG = os.environ.get("ISCP_NET_FLAG", "/tmp/iscp-net")
OFF_FLAG = os.environ.get("ISCP_OFF_FLAG", "/tmp/iscp-off")
LOG_PREFIXES = ("PWR", "SLI", "NST", "NLTF3")
power = None   # last known power state (answers to PWRQSTN also arrive as PWR..)


def log(msg):
    print(f"[eiscp] {time.strftime('%H:%M:%S')} {msg}", flush=True)


def packet(cmd):
    d = f"!1{cmd}\r".encode()
    return b"ISCP" + struct.pack(">IIB3x", 16, len(d), 1) + d


def mark(path):
    with open(path, "w") as f:
        f.write(str(time.time()))


def handle(msg):
    global power
    if msg.startswith("PWR"):
        if msg == power:
            return                      # repeated state (keepalive / queries) - not logged
        if power == "PWR01" and msg == "PWR00":
            log("receiver switched off (PWR01 -> PWR00)")
            mark(OFF_FLAG)
        power = msg
    if msg.startswith(LOG_PREFIXES):
        log(msg[:40])
    if msg == "SLI2B" or msg.startswith("NLTF3"):
        mark(NET_FLAG)


def run():
    while True:
        try:
            s = socket.create_connection((IP, 60128), 5)
            s.settimeout(5)
            log(f"connected to {IP}:60128")
        except OSError as e:
            log(f"cannot connect ({e}), retrying in 10 s")
            time.sleep(10)
            continue
        buf, last_rx = b"", time.time()
        while True:
            try:
                d = s.recv(4096)
                if not d:
                    log("receiver closed the connection")
                    break
                buf += d
                last_rx = time.time()
            except socket.timeout:
                if time.time() - last_rx > 60:          # keepalive / dead connection detection
                    try:
                        s.send(packet("PWRQSTN"))
                    except OSError:
                        break
                    if time.time() - last_rx > 130:
                        log("no answer - reconnecting")
                        break
                continue
            except OSError as e:
                log(f"connection error: {e}")
                break
            while True:
                i = buf.find(b"ISCP")
                if i < 0 or len(buf) < i + 16:
                    break
                hs, ds = struct.unpack(">II", buf[i + 4:i + 12])
                if len(buf) < i + hs + ds:
                    break
                msg = buf[i + hs:i + hs + ds].decode("latin-1").strip("\r\n\x1a\x00")[2:]
                buf = buf[i + hs + ds:]
                handle(msg)
        try:
            s.close()
        except OSError:
            pass
        time.sleep(3)


if __name__ == "__main__":
    run()
