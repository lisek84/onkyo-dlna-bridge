# Compatibility with other receivers and DLNA renderers

The project is named after the receiver it was built and tested on (Onkyo TX-NR609), but it is not tied to
it. It has two layers:

1. **Core – any DLNA / UPnP media renderer (DMR).** Soloist plays Spotify, the container serves the audio as
   an LPCM HTTP stream and tells the renderer to play it via standard UPnP AVTransport commands. Nothing in
   this layer is Onkyo-specific.
2. **Onkyo extras – eISCP.** Power-on, switching to the NET input and DLNA service, and reacting to the
   remote (NET button, power-off) use Onkyo's eISCP network protocol (TCP 60128). These only work on devices
   that speak eISCP. Disable them with `ONKYO_EISCP=no` for everything else.

## What to expect

| Device | Expected result | Settings |
|---|---|---|
| **Onkyo TX-NR609** | Fully working, tested | defaults |
| Other **Onkyo / Integra** network receivers of the same era (≈2010–2014) with DLNA renderer mode ("Play To" / "Windows 7 compatible") | Likely fully working — same eISCP protocol and a similar DLNA renderer; quirks may differ | defaults |
| Newer Onkyo / Integra / Pioneer models (eISCP + DLNA renderer) | Playback likely works; some extras may behave differently (e.g. input/service codes, display) | defaults, or `ONKYO_EISCP=no` if something misbehaves |
| Other brands' receivers and network players with a DLNA renderer (Denon, Marantz, Yamaha, Sony, …) | **Playback likely works**; title/artist usually shown; **no** automatic power-on / input switching / NET resume | `ONKYO_EISCP=no` |
| Smart TVs, Kodi, BubbleUPnP Renderer, gmrender-resurrect, other software renderers | Playback likely works if the renderer accepts `audio/L16` over HTTP | `ONKYO_EISCP=no` |
| Devices **without** a DLNA renderer (DLNA *client/player* only, AirPlay-only, Chromecast-only) | Will not work | – |

All of this except the first row is **untested** — please report results in the
[issues](https://github.com/lisek84/onkyo-spotify-connect/issues).

## With `ONKYO_EISCP=no`

Works:
- Playback started from the Spotify app, title/artist/album and cover pushed with each track (`META_UPDATE=yes`,
  `COVER_ART=yes`) — whether the cover is shown depends on the renderer
- Pausing / resuming / skipping in the Spotify app
- **Stop** on the renderer's own remote/UI pauses Spotify (`REMOTE_CONTROL=yes`), if the renderer reports
  Stop through UPnP (most do)

Not available:
- Automatic power-on (`AUTO_POWER_ON` is ignored) — the renderer must be on and reachable
- Automatic input switching — select the network/DLNA input yourself if the device needs it
- Resuming with the NET button and pausing on power-off (these come from eISCP events)

## Requirements for a renderer

- It must be a **UPnP AVTransport media renderer** reachable in the LAN (it answers SSDP on UDP 1900). If
  discovery fails, set `DMR_DESCRIPTION_URL` to its device description URL (find it with any UPnP browser).
- It must accept **`audio/L16;rate=44100;channels=2`** (raw PCM) over HTTP. Check the renderer's
  `GetProtocolInfo` sink list; most hi-fi renderers include `audio/L16`. MP3/AAC transcoding is not
  implemented (yet).
- It must be able to open a TCP connection to the host on `STREAM_PORT` (firewall, see
  [networking.md](networking.md)).

## Known differences between renderers

- **Gaps on track change** (`META_UPDATE=yes`) depend on how quickly the renderer restarts a stream. If it is
  long or annoying, use `META_UPDATE=no` (fixed display text, gapless).
- **Volume:** the Spotify slider always changes the stream level; the device volume stays on its own remote.
- Some renderers show the stream as an endless track with a running timer — that is expected for a live stream.
- The proxy pretends to be a ~3 h file. When a renderer reaches its "end" during very long uninterrupted
  playback (only possible with `META_UPDATE=no`), the container notices it and restarts the stream instead
  of treating it as a Stop.
