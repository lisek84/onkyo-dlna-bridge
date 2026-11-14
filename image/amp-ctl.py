#!/usr/bin/env python3
"""Receiver control: UPnP AVTransport (DLNA renderer / DMR) + Onkyo eISCP.

  amp-ctl.py state                      -> "STATE STATUS URI" (exit 0; 2 = DMR not responding)
  amp-ctl.py play URL [TITLE] [ARTIST] [ALBUM] [COVER_URL]
                                        -> prepare, Stop, SetAVTransportURI, Play (exit 0 = playing)
  amp-ctl.py stop [PREFIX]              -> Stop (only if the current URI starts with PREFIX)
  amp-ctl.py power                      -> power on via eISCP if in standby, wait for the DMR
  amp-ctl.py volume N / getvol          -> set / read the receiver master volume (MVL, decimal steps)
  amp-ctl.py release                    -> RESTORE_INPUT=yes: switch back to the input used before Spotify
  amp-ctl.py auto-off                   -> standby, if the container powered the receiver on and it is idle on NET

Environment: RENDERER_IP (required), ONKYO_EISCP=yes|no, AUTO_POWER_ON=yes|no,
             DMR_DESCRIPTION_URL (optional, skips discovery).
"""
import html
import os
import re
import socket
import struct
import sys
import time
import urllib.error
import urllib.request

IP = os.environ["RENDERER_IP"]
EISCP = os.environ.get("ONKYO_EISCP", "yes") == "yes"
AVT = "urn:schemas-upnp-org:service:AVTransport:1"
TIMEOUT = 6
CACHE = f"/tmp/amp-ctl.{IP}.avt-url"   # discovered AVTransport control URL
# Receiver state before Spotify took it over: "off" (we powered it on), "SLIxx" (another input) or "none".
PREV = "/tmp/amp-prev"


def log(msg):
    print(f"[amp] {time.strftime('%H:%M:%S')} {msg}", flush=True)


# ----------------------------------------------------------------- discovery --
def ssdp_locations():
    """Unicast M-SEARCH to the receiver; returns LOCATION URLs of its UPnP devices."""
    msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\n"
           f"MX: 2\r\nST: {AVT}\r\n\r\n").encode()
    found = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.5)
        s.sendto(msg, (IP, 1900))
        end = time.time() + 3
        while time.time() < end:
            try:
                data, addr = s.recvfrom(4096)
            except socket.timeout:
                break
            m = re.search(rb"(?im)^location:\s*(\S+)", data)
            if m and addr[0] == IP:
                found.append(m.group(1).decode())
    except OSError:
        pass
    return found


def avt_url():
    try:
        with open(CACHE) as f:
            cached = f.read().strip()
            if cached:
                return cached
    except OSError:
        pass
    candidates = []
    if os.environ.get("DMR_DESCRIPTION_URL"):
        candidates.append(os.environ["DMR_DESCRIPTION_URL"])
    candidates += ssdp_locations()
    candidates.append(f"http://{IP}:8888/upnp_descriptor_0")      # Onkyo 2010-2012 default
    for loc in candidates:
        try:
            body = urllib.request.urlopen(loc, timeout=TIMEOUT).read().decode("utf-8", "replace")
        except (OSError, ValueError):
            continue
        m = re.search(r"AVTransport:1</serviceType>.*?<controlURL>([^<]+)</controlURL>", body, re.S)
        if m:
            base = re.match(r"(https?://[^/]+)", loc).group(1)
            c = m.group(1)
            url = c if c.startswith("http") else f"{base}{'' if c.startswith('/') else '/'}{c}"
            try:
                with open(CACHE, "w") as f:
                    f.write(url)
            except OSError:
                pass
            return url
    return f"http://{IP}:8888/upnp_control_2"


# ---------------------------------------------------------------------- UPnP --
def soap(ctrl, action, args=""):
    env = ('<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
           's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
           f'<u:{action} xmlns:u="{AVT}"><InstanceID>0</InstanceID>{args}</u:{action}></s:Body></s:Envelope>')
    req = urllib.request.Request(ctrl, data=env.encode(), headers={
        "Content-Type": 'text/xml; charset="utf-8"', "SOAPACTION": f'"{AVT}#{action}"'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except OSError as e:
        return 0, str(e)


def tag(body, name):
    m = re.search(rf"<{name}>([^<]*)</{name}>", body)
    return html.unescape(m.group(1)) if m else ""


def state(ctrl):
    c1, b1 = soap(ctrl, "GetTransportInfo")
    if c1 != 200:
        return None
    _, b2 = soap(ctrl, "GetMediaInfo")
    return tag(b1, "CurrentTransportState"), tag(b1, "CurrentTransportStatus"), tag(b2, "CurrentURI")


def text(s):
    """Text for a DIDL element. Control characters are dropped (the receiver display shows them as '*').
    The Onkyo DMR does not decode XML entities inside DIDL-Lite (it would show "&amp;" literally, the
    official Onkyo app has the same issue), so for Onkyo the text is sent raw - the SOAP envelope is still
    escaped as a whole. Standards-compliant renderers (ONKYO_EISCP=no) get properly escaped DIDL."""
    s = "".join(ch for ch in s if ch >= " ")
    if s.strip().lower().startswith(("http://", "https://")):
        return ""                                 # a link is useless on the display
    return s if EISCP else html.escape(s)


def didl(url, title, artist="", album="", cover=""):
    pi = "http-get:*:audio/L16;rate=44100;channels=2:DLNA.ORG_PN=LPCM;DLNA.ORG_OP=01"
    d = ('<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" '
         'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"><item id="1" parentID="0" restricted="1">'
         f'<dc:title>{text(title)}</dc:title>'
         + (f'<dc:creator>{text(artist)}</dc:creator><upnp:artist>{text(artist)}</upnp:artist>' if artist else '')
         # always present, even empty: without it the Onkyo DMR takes <upnp:albumArtURI> (prefix match)
         # as the album and shows the cover URL as text
         + f'<upnp:album>{text(album)}</upnp:album>'
         # same form as the official Onkyo Remote app (any JPEG/PNG size is accepted)
         + (f'<upnp:albumArtURI dlna:profileID="JPEG_TN" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/">'
            f'{html.escape(cover)}</upnp:albumArtURI>' if cover else '')
         + '<upnp:class>object.item.audioItem.musicTrack</upnp:class>'
         f'<res protocolInfo="{pi}">{html.escape(url)}</res></item></DIDL-Lite>')
    return html.escape(d, quote=False)


# --------------------------------------------------------------------- eISCP --
def iscp(cmds, wait=1.5, until=None):
    """Send eISCP commands; collect replies for `wait` s or until until(replies) is true."""
    s = socket.create_connection((IP, 60128), 3)
    for c in cmds:
        d = f"!1{c}\r".encode()
        s.send(b"ISCP" + struct.pack(">IIB3x", 16, len(d), 1) + d)
    s.settimeout(0.2)
    buf, t, msgs = b"", time.time(), []
    while time.time() - t < wait:
        try:
            buf += s.recv(4096)
        except OSError:
            pass
        msgs = [m.decode("latin-1") for m in re.findall(rb"!1([^\r\n\x1a]+)", buf)]
        if until and until(msgs):
            break
    s.close()
    return msgs


def power():
    if not EISCP:
        return True
    try:
        r = iscp(["PWRQSTN"], until=lambda m: any(x.startswith("PWR") for x in m))
    except OSError as e:
        log(f"eISCP unreachable: {e}")
        return False
    if "PWR01" in r:
        return True
    log("receiver in standby -> PWR01")
    remember("off")
    iscp(["PWR01"], wait=0.5)
    vol = os.environ.get("POWER_ON_VOLUME", "").strip()
    if vol.isdigit():
        # only when WE switched it on - a receiver someone already uses keeps its volume
        time.sleep(2)
        set_volume(int(vol))
        log(f"power-on volume -> {vol}")
    ctrl = avt_url()
    for _ in range(20):
        time.sleep(2)
        if state(ctrl):
            return True
    log("DMR not responding after power on")
    return False


def remember(prev):
    """Store the state before Spotify took the receiver over - only once per takeover."""
    if not os.path.exists(PREV):
        with open(PREV, "w") as f:
            f.write(prev)


def set_volume(level):
    level = max(0, min(int(level), 100))
    iscp([f"MVL{level:02X}"], wait=0.3)


def get_volume():
    r = iscp(["MVLQSTN"], until=lambda m: any(x.startswith("MVL") for x in m))
    for m in r:
        if m.startswith("MVL") and len(m) >= 5:
            try:
                return int(m[3:5], 16)
            except ValueError:
                pass
    return None


def idle_on_net():
    """Receiver on, on the NET input, and not playing anything (e.g. no internet radio)."""
    want = lambda m: all(any(x.startswith(k) for x in m) for k in ("PWR", "SLI", "NST"))
    r = iscp(["PWRQSTN", "SLIQSTN", "NSTQSTN"], until=want)
    playing = any(x.startswith("NSTP") for x in r)
    return "PWR01" in r and "SLI2B" in r and not playing


def release():
    """Spotify is done with the receiver: switch back to the previous input (RESTORE_INPUT=yes)."""
    if not EISCP or not os.path.exists(PREV):
        return
    prev = open(PREV).read().strip()
    if prev.startswith("SLI") and os.environ.get("RESTORE_INPUT", "no") == "yes":
        if idle_on_net():
            log(f"restoring the previous input ({prev})")
            iscp([prev], wait=0.5)
        os.remove(PREV)


def auto_off():
    """Standby after AUTO_POWER_OFF_MINUTES - only if the container powered the receiver on."""
    if not EISCP or not os.path.exists(PREV) or open(PREV).read().strip() != "off":
        return
    if idle_on_net():
        log("receiver idle since Spotify stopped -> standby (PWR00)")
        iscp(["PWR00"], wait=0.5)
    os.remove(PREV)


def prepare():
    """Do what the official Onkyo Remote app does before DLNA playback:
    power on, select the NET input, enter the DLNA network service (NSV000).
    Without this the legacy DMR can keep rejecting Play with UPnP 705 "Transport is locked"."""
    if not EISCP:
        return True
    try:
        both = lambda m: any(x.startswith("PWR") for x in m) and any(x.startswith("SLI") for x in m)
        r = iscp(["PWRQSTN", "SLIQSTN"], until=both)
        if "PWR00" in r:
            if os.environ.get("AUTO_POWER_ON", "yes") != "yes":
                log("receiver in standby and AUTO_POWER_ON=no - not powering on")
                return False
            if not power():
                return False
            r = iscp(["SLIQSTN"], until=lambda m: any(x.startswith("SLI") for x in m))
        sli = next((x[:5] for x in r if x.startswith("SLI")), "")
        remember(sli if sli and sli != "SLI2B" else "none")
        if "SLI2B" not in r:
            log("input -> NET (SLI2B)")
            # wait for the NET menu (NLTF3...), then let it settle, otherwise NSV000 may be ignored
            iscp(["SLI2B"], wait=6, until=lambda m: any(x.startswith("NLTF3") for x in m))
            time.sleep(1.5)
        r = iscp(["NSV000"], wait=4, until=lambda m: any(x.startswith("NLT00") for x in m))
        ok = any(m.startswith("NLT00") for m in r)
        log(f"DLNA service (NSV000) -> {'OK' if ok else 'not confirmed: ' + ','.join(m[:12] for m in r)}")
        return True
    except OSError as e:
        log(f"eISCP unreachable: {e}")
        return False


def play(ctrl, url, title, artist="", album="", cover=""):
    prepare()
    soap(ctrl, "Stop")
    c, b = soap(ctrl, "SetAVTransportURI",
                f"<CurrentURI>{html.escape(url)}</CurrentURI><CurrentURIMetaData>{didl(url, title, artist, album, cover)}</CurrentURIMetaData>")
    log(f"SetAVTransportURI '{title}' / '{artist}' -> {c} {tag(b, 'errorCode')}")
    if c != 200:
        return False
    # Like the Onkyo Remote app: retry Play every second (up to 10x) on UPnP 701/705.
    for n in range(1, 11):
        c, b = soap(ctrl, "Play", "<Speed>1</Speed>")
        err = tag(b, "errorCode")
        log(f"Play ({n}) -> {c} {err} {tag(b, 'errorDescription')}")
        if c == 200 or err not in ("701", "705"):
            break
        time.sleep(1)
    if c != 200:
        return False
    st = None
    for _ in range(10):
        time.sleep(1)
        st = state(ctrl)
        if st and st[0] == "PLAYING":
            log("receiver is playing")
            return True
    log(f"state after Play: {st}")
    return False


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    if cmd == "power":
        sys.exit(0 if power() else 1)
    if cmd in ("volume", "getvol", "release", "auto-off"):
        if not EISCP:
            sys.exit(0)
        try:
            if cmd == "volume":
                set_volume(int(sys.argv[2]))
            elif cmd == "getvol":
                v = get_volume()
                print(v if v is not None else "")
            elif cmd == "release":
                release()
            else:
                auto_off()
        except (OSError, ValueError, IndexError) as e:
            log(f"{cmd} failed: {e}")
        sys.exit(0)
    ctrl = avt_url()
    if cmd == "state":
        st = state(ctrl)
        print(" ".join(st) if st else "NO_DMR")
        sys.exit(0 if st else 2)
    if cmd == "play":
        a = sys.argv[2:] + ["", "", "", "", ""]
        sys.exit(0 if play(ctrl, a[0], a[1] or "Spotify", a[2], a[3], a[4]) else 1)
    if cmd == "stop":
        st = state(ctrl)
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        if st and st[2].startswith(prefix):
            c, _ = soap(ctrl, "Stop")
            log(f"Stop -> {c}")
        sys.exit(0)
    sys.exit(64)


if __name__ == "__main__":
    main()
