#!/usr/bin/env python3
"""Read `soloist ctl now --json` from stdin and print: status, title, artist, album, cover URL
separated by 0x1F (unit separator).

Soloist's playback_state JSON (observed with Soloist 1.3.x):
  {"status": "playing",
   "item": {"decorations": {
       "identity": {"name": TITLE},
       "creators": [{"entity": {"decorations": {"identity": {"name": ARTIST}}}}, ...],
       "parent":   {"entity": {"entity_type": "album", "decorations": {"identity": {"name": ALBUM}}}},
       "visual_identity": {"cover": [{"url": URL, "size": "small|default|large|xlarge"}, ...]}}}}
Cover URLs (i.scdn.co) are rewritten to plain http - legacy receivers may not handle modern TLS,
and Spotify's image CDN serves the same files over http.
The format is not documented, so there is a heuristic fallback for other layouts.
"""
import json
import os
import sys

SEP = "\x1f"


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def names(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("name", "title", "identity", "decorations", "entity"):
            if k in v:
                n = names(v[k])
                if n:
                    return n
        return ""
    if isinstance(v, list):
        return ", ".join(x for x in (names(i) for i in v) if x)
    return ""


def first(objs, keys):
    for o in objs:
        for k in keys:
            if k in o and names(o[k]):
                return names(o[k])
    return ""


def dig(o, *path):
    for p in path:
        if isinstance(o, dict):
            o = o.get(p)
        else:
            return None
    return o


def known_layout(data):
    deco = dig(data, "item", "decorations")
    if not isinstance(deco, dict):
        return None
    title = names(dig(deco, "identity") or "")
    creators = deco.get("creators") or []
    artist = ", ".join(n for n in (names(dig(c, "entity") or c) for c in creators) if n)
    parent = dig(deco, "parent", "entity") or {}
    album = names(parent.get("decorations") or "") if parent.get("entity_type") in ("album", None) else ""
    return title, artist, album


COVER_SIZE = os.environ.get("COVER_SIZE", "default")   # small (64 px) | default (300 px) | large (640 px)


def cover_url(data):
    covers = dig(data, "item", "decorations", "visual_identity", "cover") or []
    by_size = {c.get("size"): c.get("url") for c in covers if isinstance(c, dict)}
    url = (by_size.get(COVER_SIZE) or by_size.get("default") or by_size.get("large")
           or by_size.get("small") or next(iter(by_size.values()), "") or "")
    if url.startswith("https://i.scdn.co/"):
        url = "http://" + url[len("https://"):]
    return url


def main():
    try:
        data = json.loads(sys.stdin.read())
    except ValueError:
        print(SEP.join(["idle", "", "", "", ""]))
        return
    objs = list(walk(data))
    status = next((o["status"].lower() for o in objs if isinstance(o.get("status"), str)), "idle")
    res = known_layout(data)
    if not res or not res[0]:
        track = [o["track"] for o in objs if isinstance(o.get("track"), dict)] + objs
        res = (first(track, ("title", "name", "track_name")),
               first(track, ("artists", "artist", "artist_name", "creators", "contributors", "authors",
                             "show", "show_name", "publisher", "subtitle")),
               first(track, ("album_name", "album_title", "album")))
    clean = lambda s: " ".join(s.split())[:120]
    print(SEP.join([status] + [clean(x) for x in res] + [cover_url(data)]))


if __name__ == "__main__":
    main()
