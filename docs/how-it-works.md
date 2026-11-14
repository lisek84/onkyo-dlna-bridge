# How it works

## Components (all in one container, host networking)

| Process | Role |
|---|---|
| **PulseAudio** | Provides a virtual output `dlna` (null sink, 44.1 kHz / 16 bit / stereo). |
| **Spotify Soloist** | Official Spotify Connect receiver. Plays into the `dlna` sink. Local WebSocket API is used via `soloist ctl` for status, metadata and pause/play. |
| **swyh-rs-cli** | Captures the sink monitor and serves it as an LPCM HTTP stream on `127.0.0.1:SWYH_PORT` (serve-only mode, started only while Spotify plays). |
| **dlna-proxy.py** | Serves the stream to the receiver on `STREAM_PORT` in the form legacy renderers expect; by default only to `RENDERER_IP` (`STREAM_ALLOW`). Nothing is recorded or stored. |
| **amp-ctl.py** | Controls the receiver: UPnP AVTransport (Stop / SetAVTransportURI with DIDL metadata / Play / state) and eISCP (power, NET input, DLNA service). |
| **iscp-events.py** | Persistent eISCP connection; reports NET button presses and power-off. |
| **watcher** (in `entrypoint.sh`) | State machine tying it together, polls Soloist and the renderer every 2 s. |

## Playback start

1. You select the device in Spotify → Soloist reports `playing`.
2. The watcher starts swyh-rs, waits until it listens.
3. `amp-ctl.py play`:
   1. eISCP `PWRQSTN`/`SLIQSTN`; `PWR01` if in standby (`AUTO_POWER_ON=yes`)
   2. `SLI2B` (NET input) if needed, waits for the NET menu
   3. `NSV000` – enter the **DLNA** network service (what the official Onkyo Remote app does)
   4. UPnP `Stop`, `SetAVTransportURI` (stream URL + DIDL-Lite with title/artist/album and
      `upnp:albumArtURI` → cover image), `Play`
      (retried every second up to 10× on UPnP 701/705, like the Onkyo app), then waits for `PLAYING`.
4. The receiver probes and fetches `http://HOST_IP:5901/stream.lpcm` from the proxy.

On every track change (`META_UPDATE=yes`) step 3 is repeated with the new metadata — the receiver only reads
DIDL metadata when playback starts, which is why there is a short gap.

## Legacy DMR quirks this project works around

Found on an Onkyo TX-NR609 (Mediabolic DMR/IMHTTP 1.8.x, 2011):

1. **Range probing.** Before playing, the renderer requests `Range: bytes=0-`, then `bytes=1-256`, then
   `bytes=0-` again, and wants file-like answers. swyh-rs' live-stream answers (no length, or a 64-bit
   `Content-Length` of 18446744073709551614) are rejected. The proxy pretends to be a 2 GB file
   (`Content-Length: 2000000000`, `Accept-Ranges: bytes`, `206 Partial Content`) and always serves the live stream.
2. **UPnP 705 "Transport is locked".** This error is returned by `Play` when the renderer could not open the
   stream URL (unreachable host, firewall, HTTP error) — not when "something else is playing". Worse: after
   a failed stream the renderer can stay locked and reject every later `Play`, even with a perfectly good URL.
   What reliably unlocks it is what the Onkyo Remote app does: switch to **NET**, enter the **DLNA** service
   (`NSV000`), then `SetAVTransportURI` + `Play` with retries. Therefore the proxy **never returns an error**:
   while swyh-rs is not up, it sends real-time silence.
3. **A dead URL can hang the renderer** (SOAP stops answering, no SSDP) until the receiver is unplugged
   from mains. The proxy design avoids handing the renderer anything that does not answer.
4. **Display text scrolling.** When the receiver is driven as a DLNA renderer, its network module sends
   title / artist / album to the front display as fixed 64-byte fields padded with NUL bytes (verified on
   the eISCP bus: `NTI` = text + NULs up to 64 bytes). The display scrolls the whole field, so even a short
   title slides out and the line stays empty for about 2 minutes before it comes back, then the second line
   does the same. The receiver's own DLNA player sends exact-length text and does not have this problem; the
   official Onkyo Remote app is affected exactly like this project. Terminators (CR, 0x1A) are shown as `*`
   and do not help, filling the field makes the TV text unreadable - it is a firmware limitation. The TV
   on-screen display is not affected.
5. **No entity decoding in DIDL.** The DMR takes DIDL text literally (`&amp;` would be shown as `&amp;`),
   so with `ONKYO_EISCP=yes` titles are sent unescaped inside the (escaped) SOAP envelope.
6. **DMR Max Volume.** A per-receiver volume cap applied at every DLNA start; if set to 0 the volume
   "drops to 0 every track". Set it in the receiver's web page (see [receiver-setup.md](receiver-setup.md)).

## Album cover

Soloist reports cover URLs on Spotify's image CDN (`i.scdn.co`, 64/300/640 px). The size chosen by `COVER_SIZE`
(default 300 px; the TX-NR609 also accepts 640 px but downscales it, so it looks no better there) is put into
`upnp:albumArtURI` (`dlna:profileID="JPEG_TN"`, the same form the official Onkyo Remote app uses — it sends
full-size covers too). The URL is rewritten from `https` to `http`: the CDN serves identical files over
plain HTTP and a 2011 receiver may not handle current TLS. The receiver downloads the image itself, so it needs
internet access; it is shown on the TV through the receiver's on-screen display. Disable with `COVER_ART=no`.

## Remote control mapping

In DLNA renderer mode the receiver reports very little over the network:

| Remote key | Visible to the network? | Mapped to |
|---|---|---|
| Stop | yes – renderer goes `PLAYING → STOPPED OK` | `soloist ctl pause` |
| NET | yes – eISCP `SLI2B` / `NLTF3…NET` | `soloist ctl play` (within `NET_RESUME_SECONDS` after Stop) |
| Power off | yes – eISCP `PWR01 → PWR00` | `soloist ctl pause`, no automatic power-on afterwards |
| Play, Pause, Next, Prev, FF, REW, Enter | **no** | – |

A stream failure is reported as `STOPPED ERROR_OCCURRED` and is retried (up to `AMP_MAX_TRIES` per session)
instead of being treated as Stop. Spotify sometimes resumes by itself right after a pause ("bounce"); the
watcher pauses it again within 6 s after Stop / 15 s after power-off.

## Files in `config/`

| Path | Content |
|---|---|
| `soloist-data/` | Soloist login (credentials from Spotify Connect pairing) – private |
| `soloist-cache/` | Soloist audio cache (max 500 MB) |
| `bin/` | Downloaded Soloist build |
| `home/.swyh-rs/` | Generated swyh-rs configuration |
| `container.log` | Log (`LOG_TO_FILE=yes`), rotated at 5 MB |
