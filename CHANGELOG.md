# Changelog

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
