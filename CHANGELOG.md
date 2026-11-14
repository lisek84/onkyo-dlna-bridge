# Changelog

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
