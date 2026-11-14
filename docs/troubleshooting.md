# Troubleshooting

Read the log first: `docker compose logs -f`, Container Manager → Log, or `config/container.log`.
When posting logs publicly, remove your API key and account name.

## The device does not appear in the Spotify app

- Is the container running and does the log show `ready, device_name=…`?
- Host networking (`network_mode: host`) is mandatory. Docker Desktop / Podman Desktop VMs do not work.
- Phone and host must be in the same LAN/VLAN; mDNS (UDP 5353) must not be blocked (firewall, "client
  isolation" / guest Wi-Fi on the access point, multicast filtering between VLANs).
- `ERROR: could not download Soloist` – the host needs internet access on start.

## The device appears, playback "runs" in the app, but the receiver does nothing

Look for `[amp]` lines in the log:

| Log | Meaning / fix |
|---|---|
| `Play (…) -> 500 705 Transport is locked` ×10 and **no** `[proxy] <receiver-ip> GET` lines | The receiver cannot reach the stream. **Allow TCP 5901 from the receiver's IP in the host firewall** ([networking.md](networking.md)); check `HOST_IP`. |
| `[proxy] … GET` lines present, but still 705 | Power-cycle the receiver (unplug ~30 s), then try again. |
| `[proxy] <ip> GET … -> 403 (not in STREAM_ALLOW)` with the receiver's IP | The receiver's IP differs from `RENDERER_IP` (DHCP?) – fix `RENDERER_IP` / reserve the IP, or list a subnet in `STREAM_ALLOW`. |
| `eISCP unreachable` | Wrong `RENDERER_IP`, receiver unplugged, or Network Standby off. |
| `DMR not responding` / state `NO_DMR` | Renderer hung – unplug the receiver ~30 s. |
| `receiver in standby and AUTO_POWER_ON=no` | Switch it on, or set `AUTO_POWER_ON=yes`. |

## It plays, but I hear nothing

- **DMR Max Volume** on the receiver's web page is 0 → set 60–70 ([receiver-setup.md](receiver-setup.md)).
- Volume in the Spotify app (digital stream volume) is very low.
- The receiver shows "NET" and a title but no sound for a few seconds: normal startup buffering.

## Short gaps at the start of every track

Expected with `META_UPDATE=yes` – the receiver only reads title/artist when DLNA playback starts.
Set `META_UPDATE=no` for gapless playback with a fixed display text.

## Remote buttons

Only **Stop** (pause), **NET** (resume after Stop) and **power off** (pause) can be mapped; the receiver does
not report other keys in DLNA mode. NET resumes only within `NET_RESUME_SECONDS` after a Stop/power off and
only if `REMOTE_CONTROL=yes`.

## The receiver switches itself on

Only happens when Spotify starts playing on this device and `AUTO_POWER_ON=yes`. If you switched the receiver
off, the container pauses Spotify and does not power it on again until a new playback is started from the app.

## Soloist stopped working after ~3 months

Builds expire after 90 days (exit code 10). The container restarts and downloads a new build automatically
if `restart: unless-stopped` is set and the host has internet access. Check `config/bin/` and the log line
`downloaded a new Soloist build`.

## Collecting more information

- Soloist verbose log: add `SOLOIST_EXTRA_ARGS=-v` to `soloist.env`.
- Every request of the receiver is logged by the proxy (`[proxy] …`), every eISCP event by `[eiscp] …`.
