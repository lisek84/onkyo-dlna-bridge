# onkyo-dlna-bridge

English | [Polski](README.pl.md)

[![image](https://github.com/lisek84/onkyo-dlna-bridge/actions/workflows/image.yml/badge.svg)](https://github.com/lisek84/onkyo-dlna-bridge/actions/workflows/image.yml)

Spotify for audio gear that doesn't have a working Spotify of its own. A small container runs Spotify
Soloist (Spotify's official headless client) and streams what it plays to a DLNA/UPnP renderer, so the
device shows up in the Spotify app like any other speaker.

I wrote it for my Onkyo TX-NR609, whose built-in Spotify died together with libspotify, and that's where it
works best: the receiver switches itself on, changes input, shows the track on its display and the cover on
the TV, and reacts to a few buttons on the remote. Other DLNA renderers (receivers, network players, TVs,
Kodi) should get the music and usually the track info, just without the Onkyo-specific parts. See
[docs/compatibility.md](docs/compatibility.md).

Not affiliated with or endorsed by Spotify or Onkyo. The receiver does not become a certified Spotify Connect
device. Personal, non-commercial use only.

<p align="center">
  <img src="docs/images/receiver-display.jpg" alt="Onkyo TX-NR609 front display showing the current Spotify track and artist" width="49%">
  <img src="docs/images/tv-osd-cover.jpg" alt="TV showing the receiver's DLNA screen with album cover, title, artist and album" width="37%">
</p>
<p align="center"><sub>Front display with the current track, and the receiver's on-screen display on the TV (over HDMI).</sub></p>

## Background

The TX-NR609 is a perfectly good amplifier. It had Spotify in its NET menu until Spotify shut down
libspotify, and Onkyo never shipped anything to replace it. The menu entry is still there; it just doesn't
work. I didn't want to replace a working amplifier because of that.

I also didn't want to hack the receiver or use an unofficial Spotify client, so the project sticks to
official pieces:

- Spotify Soloist with your own developer key. It isn't bundled here; every install downloads it from
  Spotify's CDN.
- The receiver is controlled only through what it offers on the network anyway: its DLNA renderer and
  Onkyo's eISCP protocol (the same one the Onkyo Remote app uses). The firmware isn't touched.
- The audio stream is served only to your receiver (other clients are refused by default) and nothing is
  recorded.

If you have an old receiver that lost its streaming services the same way, maybe this helps.

## How it works

```
 Spotify app ──Spotify Connect──►  Soloist ─► PulseAudio ─► swyh-rs ─► HTTP proxy ──DLNA/HTTP──► receiver
 (phone/PC)                        └──────────────── container (host network) ──────┘    ▲
                                    receiver control: UPnP AVTransport + eISCP (TCP 60128) ┘
```

Soloist plays into a virtual PulseAudio sink, swyh-rs turns that into a plain LPCM (44.1 kHz/16 bit) HTTP
stream, and a small proxy serves it to the receiver in a way its old DLNA renderer accepts. A watcher script
follows Soloist's state and drives the receiver: start playback, send title/artist/album/cover on every track
change, pause when you press Stop, and so on.

More in [docs/how-it-works.md](docs/how-it-works.md). If you want to build on this, everything I found out
about the receiver itself (chips, eISCP messages, DLNA quirks, which remote keys can be seen on the network)
is in [docs/receiver-internals.md](docs/receiver-internals.md).

## What works

With any DLNA renderer: the device appears in the Spotify app, plays in LPCM, and gets title, artist, album
and cover with every track (for podcasts, the show name). Soloist updates itself, which matters because its
builds expire after 90 days.

On Onkyo/Integra receivers, additionally:

- switches the receiver on and to NET/DLNA when you start playing;
- Stop on the remote pauses Spotify, NET resumes it, switching the receiver off pauses it;
- optional extras: NET as "next track" during playback, handing playback back to the phone when the
  receiver is switched off, Spotify slider controlling the receiver volume, a start-up volume, switching back
  to the previous input (e.g. TV) afterwards, and automatic standby.

Play, Pause, Next and Previous on the remote can't be used. In DLNA mode the receiver handles those keys
internally and doesn't report them on the network (checked with both eISCP and UPnP).

Tested so far: Onkyo TX-NR609 with a Synology DS718+ (x86_64, DSM 7.2, Container Manager). Other x86_64
Linux hosts with Docker or Podman use the same image and should be fine. The ARM build (`Dockerfile.arm`,
Raspberry Pi) and Windows/WSL2 ([docs/windows.md](docs/windows.md)) are untested. If you try it on other
hardware, please open an [issue](https://github.com/lisek84/onkyo-dlna-bridge/issues) either way.

## What you need

- A Spotify Soloist API key. It's free, but has to be created from a Premium account; after that, Free
  accounts can play to the device too. See [docs/spotify-developer-key.md](docs/spotify-developer-key.md).
- A Linux host (NAS, Raspberry Pi, anything) on the same LAN, with Docker or Podman and host networking.
  It needs about 100 MB of RAM and runs on x86_64, arm64 and armv7.
- The receiver on the network with a fixed IP and two settings checked:
  [docs/receiver-setup.md](docs/receiver-setup.md).
- The receiver must be able to connect to the host on TCP 5901 (`STREAM_PORT`), and mDNS (UDP 5353) has to
  reach the host. A firewall silently blocking 5901 is the most common reason nothing plays; see
  [docs/networking.md](docs/networking.md).

## Setup

```bash
git clone https://github.com/lisek84/onkyo-dlna-bridge.git
cd onkyo-dlna-bridge
cp soloist.env.example soloist.env
nano soloist.env               # SOLOIST_API_KEY, RENDERER_IP, DEVICE_NAME, PUID/PGID
docker compose up -d --build   # Raspberry Pi: set dockerfile: Dockerfile.arm in compose.yaml first
docker compose logs -f
```

Then open Spotify on your phone, pick `DEVICE_NAME` from the device list and press play. The first time,
Soloist logs in with the account that picked it; after that it reconnects by itself.

There's also a prebuilt image (amd64, arm64) at `ghcr.io/lisek84/onkyo-dlna-bridge`. To use it, replace the
`build:` block in `compose.yaml` with `image: ghcr.io/lisek84/onkyo-dlna-bridge:latest`.

Step-by-step guides: [Synology DSM](docs/synology.md), [Linux, Raspberry Pi, Podman/Quadlet](docs/linux.md),
[Windows (WSL2)](docs/windows.md).

## Settings

Everything is configured in `soloist.env`; [soloist.env.example](soloist.env.example) has comments for each
option.

| Variable | Default | |
|---|---|---|
| `SOLOIST_API_KEY` | (required) | Your Soloist API key |
| `RENDERER_IP` | (required) | IP of the receiver |
| `DEVICE_NAME` | `Onkyo Receiver` | Name shown in the Spotify app |
| `HOST_IP` | auto | LAN IP of the host; set it if the host has several networks |
| `PUID` / `PGID` | `1000` / `1000` | Owner of `./config` (Synology: usually `1026` / `100`) |
| `STREAM_PORT` | `5901` | Port the receiver pulls the audio from; must be open in the firewall |
| `STREAM_ALLOW` | `renderer` | Who may fetch the stream: `renderer` (only `RENDERER_IP`), a list of IPs/subnets, or empty for anyone |
| `SWYH_PORT` | `5911` | Internal capture port, localhost only |
| `INITIAL_VOLUME` | `70` | Initial Spotify volume |
| `META_UPDATE` | `yes` | Send title/artist on every track (2–4 s gap at the start of each track); `no` = gapless, fixed `PLAY_TITLE` |
| `PLAY_TITLE` | `Spotify` | Display text when no metadata is sent |
| `COVER_ART` | `yes` | Send the album cover |
| `COVER_SIZE` | `default` | `default` (300 px), `large` (640 px) or `small` (64 px) |
| `ONKYO_EISCP` | `yes` | Use Onkyo's eISCP protocol; set `no` for other renderers |
| `AUTO_POWER_ON` | `yes` | Switch the receiver on when playback starts |
| `REMOTE_CONTROL` | `yes` | Stop pauses, NET resumes, power off pauses |
| `NET_RESUME_SECONDS` | `120` | How long after Stop the NET button resumes (NET also opens the NET menu) |
| `NET_NEXT` | `no` | `yes`: NET during playback skips to the next track (press Stop first to use the NET menu) |
| `POWER_OFF_ACTION` | `pause` | When the receiver is switched off: `pause`, or `release` to pause and disconnect so the phone takes over |
| `VOLUME_SYNC` | `no` | Spotify volume slider and receiver volume follow each other |
| `VOLUME_MAX` | `50` | Receiver volume that equals 100 % in Spotify (hard limit) |
| `POWER_ON_VOLUME` | empty | Volume set when the container switches the receiver on; empty means the receiver keeps its usual volume |
| `RESTORE_INPUT` | `no` | Switch back to the previous input (e.g. TV) when Spotify is done |
| `AUTO_POWER_OFF_MINUTES` | `0` | Standby after N minutes without Spotify, if the container switched the receiver on |
| `IDLE_STOP_SECONDS` | `300` | Stop streaming after this long paused |
| `LOG_TO_FILE` | `yes` | Also log to `config/container.log` |

The two volume options are independent. With neither set, the receiver's volume is left alone and the Spotify
slider only changes the stream level. `POWER_ON_VOLUME` applies only when the container itself switches the
receiver on from standby, and never to a receiver that's already on; leave it empty and the receiver starts at
whatever volume it had last. With `VOLUME_SYNC=yes`, the Spotify slider is first moved to match the receiver's
current volume (the receiver itself doesn't change), and from then on they follow each other.

## Using it

Pick the device in Spotify and press play; after 8 to 15 seconds the receiver is on, on NET, and playing.
Skipping tracks happens in the Spotify app as usual, and the display follows. Stop on the remote pauses
Spotify; NET within two minutes after that resumes it. Switching the receiver off pauses Spotify, and the
container won't switch it back on. The remote's volume buttons control the amplifier; the Spotify slider
controls the stream, or the amplifier if `VOLUME_SYNC=yes`.

## Docs

- [Compatibility with other receivers and renderers](docs/compatibility.md)
- [How it works](docs/how-it-works.md)
- [Receiver internals (for developers)](docs/receiver-internals.md)
- [Why Soloist and not librespot/spotifyd](docs/why-soloist.md)
- [Getting a Soloist API key](docs/spotify-developer-key.md)
- [Receiver setup](docs/receiver-setup.md)
- [Networking and firewall](docs/networking.md)
- [Troubleshooting](docs/troubleshooting.md)

## Legal

Not affiliated with, endorsed, sponsored or certified by Spotify or Onkyo. "Spotify", "Spotify Connect",
"Spotify Soloist" and "Onkyo" are trademarks of their owners and are used only to describe compatibility; no
logos or brand assets are used.

Personal, non-commercial use only, as the Spotify developer terms require. Audio is streamed live to your own
receiver (`STREAM_ALLOW=renderer` by default) and is never recorded or stored.

Spotify Soloist is not distributed with this project. The container downloads it from Spotify's CDN at
runtime, and its use is covered by the terms you accept when you create the API key (see the
[Soloist documentation](https://developer.spotify.com/documentation/soloist)). The key is personal; don't
share it.

The container image contains this project's scripts, Debian packages and the
[swyh-rs](https://github.com/dheijl/swyh-rs) CLI binary (MIT © dheijl, license included at
`/usr/share/doc/swyh-rs/LICENSE`). It does not contain Soloist.

The code here is MIT licensed, © Lisek ([lisek84](https://github.com/lisek84)). See [LICENSE](LICENSE).
