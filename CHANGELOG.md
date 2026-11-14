# Changelog

## 1.4.1

- Fix: `VOLUME_SYNC` forced Soloist's PulseAudio stream to 100 %, which is the Spotify volume itself – the slider
  jumped to 100 % and the receiver to `VOLUME_MAX`. The stream volume is no longer touched; the virtual output
  gets the inverse gain instead (full-level stream, verified with PulseAudio 17).

## 1.4.0

- Optional receiver integration (all off by default, eISCP):
  - `VOLUME_SYNC` + `VOLUME_MAX`: Spotify volume slider <-> receiver master volume, both ways, with a hard limit.
  - `POWER_ON_VOLUME`: volume set only when the container switches the receiver on.
  - `RESTORE_INPUT`: back to the previous input (e.g. TV) when Spotify is done.
  - `AUTO_POWER_OFF_MINUTES`: standby after N minutes without Spotify, if the container switched the receiver on.
- `NET_RESUME_SECONDS` default lowered to 120 s: the NET button also opens the NET menu, so a later visit to the
  menu no longer resumes Spotify.

## 1.3.1

- Fix (important): after moving Spotify playback to another device (e.g. the phone), the receiver's remote
  (NET) could still resume playback - on the phone - and start the receiver with silence. The container now
  follows Soloist's "active device" state: while another device is active it ignores the receiver completely,
  and it releases the receiver (stops its own stream) when playback moves away.
- Docs: tested list of remote keys and what they do in DLNA renderer mode (Next/Previous cannot be mapped).
- Fix: Spotify could resume by itself after you stopped it and used another NET source (e.g. internet radio).
  A repeated "input = NET" status (sent by the receiver after a radio stream stops, or as an answer to another
  app's query) was taken as a NET button press. Now only a real switch from another input (or the NET top menu)
  counts, and if the receiver starts playing another source after the Stop, NET no longer resumes Spotify.

## 1.3.0

- New `COVER_SIZE`: album cover size sent to the renderer - `default` (300 px, unchanged default), `large` (640 px)
  or `small` (64 px). The TX-NR609 accepts 640 px but downscales it itself, so it brings no visible gain there.

## 1.2.1

- Fix: titles/artists with `&`, `<`, `>` were shown as `&amp;` etc. on Onkyo receivers (their DMR does not
  decode entities inside DIDL); control characters are stripped from metadata.
- Docs: front display scrolling quirk of the Onkyo DMR (64-byte NUL-padded fields, also in the official app)
  documented as a known firmware limitation.

## 1.2.0

- **Renamed** from `onkyo-spotify-connect` to **`onkyo-dlna-bridge`** (repository, image
  `ghcr.io/lisek84/onkyo-dlna-bridge`, container names) to follow Spotify's branding guidelines
  (no "Spotify" in product names).
- New `STREAM_ALLOW` (default `renderer`): the audio stream is served only to the receiver; other devices get
  HTTP 403. Accepts a list of IPs/subnets, or empty for the previous behaviour.
- swyh-rs now listens on localhost only (the proxy falls back to `HOST_IP` if needed).
- README/docs: clearer disclaimers (no affiliation/certification, personal non-commercial use, nothing is
  recorded), Premium needed only to create the Soloist key.

## 1.1.1

- Container images now include the swyh-rs MIT license (`/usr/share/doc/swyh-rs/LICENSE`), as required
  for redistributing its binary; README states what the published image contains (and that it does not
  contain Spotify Soloist)

## 1.1.0

- Album cover sent with the track metadata (`upnp:albumArtURI`, `COVER_ART=yes`), shown on the TV via the
  receiver's on-screen display (tested on TX-NR609)
- Fix: very long uninterrupted playback (end of the pretended ~3 h stream) is restarted instead of being
  treated as a remote Stop

## 1.0.0 – first public release

- Spotify Soloist → PulseAudio → swyh-rs → HTTP proxy → DLNA renderer pipeline in one container
- Onkyo eISCP integration: power on, NET input + DLNA service before playback, persistent event listener
- Workarounds for legacy Mediabolic DMR firmware (Range probing, UPnP 705 lock, never-failing proxy)
- Track title / artist / album on the receiver display
- Remote mapping: Stop → pause, NET → resume, power off → pause (with protection against Spotify resuming by itself)
- Automatic Soloist download/update for x86_64, arm64, arm32
- Separate Synology, Docker/Podman Compose and Podman Quadlet deployments
- `ONKYO_EISCP=no` mode for other DLNA renderers; SSDP discovery of the renderer; host IP auto-detection
