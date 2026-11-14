# Why Spotify Soloist (and not librespot, spotifyd, raspotify, SpotConnect …)

## The problem

Receivers like the Onkyo TX-NR609 shipped with a Spotify client built on **libspotify**, Spotify's
old SDK. Spotify shut libspotify down, so the built-in "Spotify" entry stopped working for good.
The receiver's network module (a 2010-era ARM9 SoC with 32 MB RAM, Linux 2.6, uClibc) cannot run a
modern Spotify Connect client itself (the official Soloist builds need ARMv7+/glibc 2.38+), and
modifying the vendor firmware is something this project deliberately avoids.

So the Spotify Connect endpoint has to run **somewhere else** in the house and feed the receiver
through an interface it already has: its **DLNA media renderer** (DMR).

## Options that were evaluated

| Option | What it is | Why not (here) |
|---|---|---|
| **librespot** / spotifyd / raspotify | Open-source, reverse-engineered Spotify Connect clients | Depend on an unofficial protocol implementation; Spotify can (and repeatedly did) break them with server-side changes. On some accounts playback fails with *"Failed to get audio key"* — Spotify refuses keys to third-party clients, and there is no configuration fix for that. |
| **SpotConnect / spotupnp** (cspot based) | Ready-made Spotify Connect → UPnP/DLNA bridge | Same root cause: it was tested first and the device appeared in Spotify and volume control worked, but every track failed with *"Failed to get audio key"*. |
| Spotify Connect hardware dongle / streamer | e.g. a small network streamer on the receiver's optical input | Works, but costs money, needs an extra box and an input, and loses the receiver's own display / power integration. |
| **Spotify Soloist** | **Spotify's official** headless Spotify Connect receiver for Linux (x86_64, arm64, arm32) | ✅ Official, supported by Spotify, receives audio keys like any first-party device, auto-update path via CDN. |

## Why Soloist is a good fit

- **Official** – it is Spotify's own client, intended exactly for "turn a Linux box into a network speaker".
  No reverse engineering, no audio-key failures, no breakage after Spotify server changes.
- **Simple authentication** – one personal API key from the developer dashboard; the first connection from
  the Spotify app logs it into your account (Spotify Connect pairing), no password in config files.
- **Headless, scriptable** – it outputs to PulseAudio/PipeWire and has a local WebSocket API and a
  `soloist ctl` command (status, metadata, pause/play). This project uses it for track metadata and for
  mapping the receiver remote to pause/resume.

## Trade-offs you accept

- **Spotify Premium is required** (for the account creating the key).
- **Builds expire after 90 days.** The container downloads the current build from Spotify's CDN on every
  start (`curl -z`, only when newer), and Soloist exits with code 10 when expired — the restart policy
  restarts the container, which fetches a fresh build. Keep `restart: unless-stopped`.
- **No redistribution.** Spotify does not allow redistributing Soloist binaries, so the image does not
  contain it; it needs internet access on start.
- **Extra hop through DLNA.** The receiver pulls a live LPCM stream over HTTP. That adds a few seconds of
  latency when starting/resuming and a short gap when the display metadata is refreshed per track
  (disable with `META_UPDATE=no`). Volume in the Spotify app changes the stream level, not the amplifier.

## Why swyh-rs and a proxy in between

Soloist plays into a virtual PulseAudio sink. [swyh-rs](https://github.com/dheijl/swyh-rs) ("Stream What
You Hear") captures that sink and serves it as a DLNA-compatible LPCM HTTP stream. The 2011 renderer is
picky about how a stream is served (see [how-it-works.md](how-it-works.md)), so a tiny Python proxy sits in
front of swyh-rs and presents the stream the way the receiver expects. Receiver control (starting
playback, metadata, remote mapping) is done by this project's own scripts, not by swyh-rs.
