# Receiver internals – technical reference (Onkyo TX-NR609)

Everything this project learned about the receiver, written down so that others can extend the project (or build
something else for these receivers) without repeating the research. It is based on:

- observing the receiver's network interfaces (UPnP/DLNA, eISCP, HTTP) while it was driven by this project, by the
  official *Onkyo Remote* app and by the receiver's own menus;
- the receiver's publicly available firmware package and service manual (Ref. No. 4264; only facts such as chip
  names are summarised here – no code, schematics or document content are reproduced);
- the publicly documented Onkyo eISCP protocol.

Model tested: **Onkyo TX-NR609** (2011). Many Onkyo/Integra network receivers of 2010–2013 share the same network
platform, so most of this is likely to apply to them too – but it was verified only on the TX-NR609.

> Nothing here requires modifying the receiver. All interfaces described are the ones the receiver offers on the
> network by design.

---

## 1. Architecture at a glance

The receiver has a main microcontroller (front panel, inputs, volume, amplifier, protection) and a **TI DA830**
processor that does two jobs at once: its C674x DSP core decodes and processes the audio (surround formats, DSP
modes), and its ARM926 core runs the embedded Linux that provides Ethernet, internet radio, the network services
menu, DLNA, USB/iPod and the web setup page. Everything "network" in this document lives on that ARM core.

| Item | Value |
|---|---|
| Network/DSP processor | **TI DA830** (`D830K013BZKB400Z`): ARM926EJ-S (ARMv5TE, no FPU) + C674x DSP, 20 MHz crystal |
| Its memory | 2 × 256 Mbit SDRAM (`IS42S16160C` / `EM63A165TSB`) = 64 MB; 256 Mbit NAND flash (`NAND256W3A2`) |
| Ethernet PHY | Micrel/Microchip `KSZ8051RNL` (10/100, RMII) |
| USB / iPod | USB host of the DA830 on the front port; Apple authentication coprocessor (`MFI341S2164`) |
| OS (ARM core) | Embedded Linux 2.6.33 (MontaVista userland), uClibc, squashfs root |
| DLNA stack | Mediabolic (DMR/IMHTTP 1.8.x) – UPnP AV renderer (DMR) and player (DMP) |
| Network services (menu, as of the last firmware) | vTuner, Last.fm, Napster, **Spotify (libspotify – shut down by Spotify, no longer works)**, AUPEO!, My Favorites, DLNA |
| Main microcontroller | Renesas (NEC) V850ES `uPD70F3746` ("MAIN") + SPI EEPROM for settings |
| HDMI / video | Analog Devices `ADV7844` (HDMI receiver/decoder), Silicon Image `SiI9489` (HDMI switch), Marvell `88DE2755` ("Kyoto-G2H" video processor, own DDR3 + SPI flash), Toshiba `TMPM361` (HDMI/video controller), `TMDS141` buffer |
| Audio converters | TI `PCM9211` (S/PDIF receiver + ADC, coax/optical inputs), `PCM1690` (8-channel DAC), `PCM1754` (2-channel DAC for the Zone 2 / NET path) |
| Analogue control | Renesas `R2A15218FP` (electronic volume / input selector), NJR `NJW1328` |
| Control protocol | eISCP on TCP 60128 |
| Web setup | HTTP on port 80 ("Unit information" page) |
| UPnP device | HTTP on port 8888 |

The DA830 sits on the HDMI/DSP board (board code `BAHDM-0685`) and talks to the main microcontroller over SPI with the same ISCP message set that is exposed on the network as eISCP. That is why display texts, input changes, power state etc. are visible to any eISCP client.

The firmware update package contains separate images for the main microcontroller and the DA830. This project does
not modify, unpack or need the firmware.

Why the receiver cannot run a modern Spotify client itself: the official Spotify Soloist builds are linked against
glibc ≥ 2.38 and PulseAudio/PipeWire, and the 32-bit build targets a newer ARM architecture than the ARMv5TE
ARM926 core – while the receiver has an old uClibc system and no such audio stack (and the 64 MB of RAM are shared
with everything the receiver already does). Hence the external bridge.

---

## 2. Network ports

| Port | Protocol | Use |
|---|---|---|
| TCP 60128 | eISCP | control & status (power, input, volume, NET menu, display texts) |
| TCP 8888 | HTTP / UPnP | device description `/upnp_descriptor_0`, SOAP control, GENA events |
| UDP 1900 | SSDP | discovery (answers unicast M-SEARCH) |
| TCP 80 | HTTP | web setup page |

With **Network Standby** enabled, the network part stays reachable in standby (eISCP and UPnP answer while the amplifier is off).
After a mains power cycle it may stay offline until the receiver is switched on once.

---

## 3. eISCP (TCP 60128)

### Packet format

```
"ISCP" | header size (uint32 BE, = 16) | data size (uint32 BE) | version (1 byte, = 0x01) | 3 reserved bytes
data:  "!1" + COMMAND + PARAMETER + "\r"           (receiver -> client ends with 0x1A "\r\n")
```

Example – power on: `ISCP 00000010 00000008 01 000000` + `!1PWR01\r`.

Notes:
- The receiver **broadcasts every answer and status change to all connected clients**. An answer to another
  app's query (e.g. `SLIQSTN`) arrives as `SLI2B` exactly like a real input change – track the previous value to
  detect real transitions.
- While something plays on NET, `NTM` (elapsed time) arrives every second – read loops must be time-limited.
- One persistent connection is enough for events; the receiver keeps it open (send a query every ~60 s as keepalive).

### Commands and messages used by this project

| Message | Direction | Meaning |
|---|---|---|
| `PWRQSTN` / `PWR00` / `PWR01` | query / status / set | power standby / on |
| `SLIQSTN` / `SLIxx` | query / status / set | input selector; `SLI2B` = NET, `SLI01` = CBL/SAT, `SLI02` = GAME … |
| `MVLQSTN` / `MVLxx` | query / status / set | master volume, 2 hex digits (e.g. `MVL28` = 40); remote/knob changes are reported |
| `AMT00/01` | status | mute |
| `NSV000` | set | open the **DLNA** network service (as the Onkyo Remote app does before DLNA playback) |
| `NSTxxx` | status | NET play status: `NSTP--` playing, `NSTS--` stopped |
| `NLT…` | status | NET list/menu title, e.g. `NLTF3…NET` = NET top menu, `NLT00…DLNA` = DLNA service |
| `NLS…` | status | NET list items / cursor |
| `NTI` / `NAT` / `NAL` | status | track title / artist / album (see §4, quirk 8) |
| `NTR` | status | track number / count |
| `NTM` | status | elapsed time `mm:ss/mm:ss` (every second) |
| `NJA` | status | album art (jacket) sent in chunks to network apps |
| `NTCSTOP` etc. | set | NET transport keys – answered with `NTCN/A` when not applicable |

In DMR (DLNA renderer) mode the receiver does **not** answer `NTIQSTN`/`NATQSTN`/`NALQSTN`; it only pushes them when
playback starts.

---

## 4. UPnP / DLNA renderer (DMR)

| Item | Value |
|---|---|
| Device description | `http://<ip>:8888/upnp_descriptor_0` |
| AVTransport control | `/upnp_control_2` (RenderingControl `/upnp_control_0`, ConnectionManager `/upnp_control_1`) |
| Events (GENA) | `/upnp_event_0..2` |
| Sink formats (`GetProtocolInfo`) | `audio/L16` 44.1/48 kHz mono/stereo (`DLNA.ORG_PN=LPCM`), MP3, WMA (base/full/lossless, WMDRM), AAC (ADTS / ISO), `audio/wav` – **no FLAC** |
| Transport states | `STOPPED`, `PLAYING`, `TRANSITIONING`, `NO_MEDIA_PRESENT`; status `OK` / `ERROR_OCCURRED` |
| Actions | SetAVTransportURI, SetNextAVTransportURI, Play, Pause, Stop, Seek, Next, Previous, Get*Info … |

### Quirks (all verified)

1. **UPnP error 705 "Transport is locked"** on `Play` means *"I could not open the stream URL"* (firewall,
   unreachable host, HTTP error) – not that something else is playing. After a failed stream the renderer can stay
   locked and reject every later `Play`, even with a good URL.
2. **What reliably works** (it is what the official Onkyo Remote app does): eISCP `SLI2B` (NET input) → wait for the
   NET menu → `NSV000` (DLNA service) → `Stop` → `SetAVTransportURI` → `Play`, retrying `Play` every second (up to
   10×) while it answers 701/705.
3. **Stream probing.** Before playing, the renderer requests `Range: bytes=0-`, `bytes=1-256`, then `bytes=0-` again
   (User-Agent `Mediabolic-IMHTTP/1.8.x … DLNADOC/1.50`) and expects file-like answers: `Content-Length` (keep it
   below 2³¹ – a 64-bit "endless" length is rejected), `Accept-Ranges: bytes`, `206 Partial Content`.
4. **Never hand it a dead URL** – the DMR can hang completely (no SOAP, no SSDP) until the receiver is unplugged from
   mains for ~30 s. Standby does not restart the DA830.
5. **No entity decoding in DIDL-Lite metadata.** Text inside `CurrentURIMetaData` is taken literally:
   `&amp;` is displayed as `&amp;`, numeric references (`&#13;`) are not decoded either (also at the SOAP level).
   Send the DIDL text unescaped inside the (escaped) SOAP envelope. Control characters are displayed as `*`.
6. **Metadata used:** `dc:title`, `dc:creator`/`upnp:artist`, `upnp:album`, `upnp:albumArtURI` (cover). The `res`
   `duration` attribute is accepted but not shown. Metadata is read only when playback starts – to refresh the
   display for a new track, send `SetAVTransportURI` + `Play` again (≈ 2–4 s gap).
7. **Album cover:** `<upnp:albumArtURI dlna:profileID="JPEG_TN" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/">URL</…>`.
   Any JPEG size is accepted (64–640 px tested); the receiver downscales it itself for its TV on-screen display.
   The receiver fetches the image over plain HTTP (Spotify's `i.scdn.co` serves the same files over http).
   **Always send `<upnp:album>` (empty if there is none) before `<upnp:albumArtURI>`** – without it the DMR matches
   the album by tag-name prefix, takes `upnp:albumArtURI` instead and shows the cover URL as the album.
8. **Front display scrolling (firmware limitation).** In DMR mode the DA830 software sends `NTI`/`NAT`/`NAL` as fixed
   64-byte fields padded with NUL bytes; the front display scrolls the whole field, so a short title slides out and
   the line stays empty for ~2 minutes. The built-in DLNA player (DMP) sends exact-length text and scrolls properly.
   The official Onkyo app is affected the same way. Not fixable from outside (CR/0x1A terminators, filling the field,
   injecting `NTI` via eISCP – all tested, none helps). The TV on-screen display is not affected.
9. **"DMR Max Volume"** (web setup, field `win7vol`) is a volume cap applied whenever DLNA playback starts; `0` makes
   the volume drop to zero on every track. **"Auto Play"** (web setup) is unrelated to error 705.
10. **Stop/Play semantics.** The remote's Stop puts the DMR into `STOPPED OK`; Play on the remote does not restart a
    stopped DMR stream. Pause on the remote has no effect in DMR mode.

---

## 5. Remote control in DMR mode (key by key)

| Key | Network-visible | Effect on the receiver |
|---|---|---|
| Stop | DMR `PLAYING → STOPPED OK` | stops playback |
| NET | `SLI2B` (from another input) or `NLTF3…NET` (already on NET) | NET input / NET top menu |
| Power | `PWR01 → PWR00`, preceded by `NSTS--` (~6 s earlier) | standby |
| Vol ± / knob | `MVLxx` | master volume |
| ◀ / Return, Menu, Enter | `NLT`/`NLS` menu events | navigate the NET menu (leaves the playback screen, may stop it) |
| CH ±, digits 1–9 | `NLT…My Favorites`, `NSTP` | switch to an internet-radio favourite |
| Play, Pause, Next, Prev, FF, REW, ▲ ▼ ▶, Display, Dimmer, Mode | nothing | – |

Pressing NET while the DMR plays does **not** stop playback – only the screen changes to the NET menu (one `NLTF3…`
message). Further NET presses while the menu is shown send nothing; the next `SetAVTransportURI` + `Play` returns the
playback screen. Arrow-key navigation also produces `NLTF3…` messages (with a different cursor position), so "NET pressed" and "menu
navigation" cannot be told apart reliably.

---

## 6. Web setup page (port 80)

"Unit information": Friendly Name (DLNA renderer name), **DMR Max Volume (0–100)** (`win7vol`), **Auto Play
(Yes/No)**, network information. Saved with a POST to `info.cgi`.

---

## 7. How the official Onkyo Remote app plays music from the phone

Observed on the network (useful as a reference implementation):

1. eISCP connection, queries of power/input/volume/etc.
2. `SLI2B` (NET), then `NSV000` (DLNA service).
3. The phone runs its own HTTP server serving the file with full `Range` support (`206`, real `Content-Length`).
4. `SetAVTransportURI` with DIDL-Lite: `upnp:class` `object.item`, `res duration="<seconds>"`,
   `protocolInfo="http-get:*:audio/mpeg:DLNA.ORG_OP=01"`, `upnp:albumArtURI` (`JPEG_TN`), title/creator/album.
5. `Play`, retried every second on UPnP error 701, up to 10 times.
6. Subscribes to AVTransport events (GENA) for state changes.

---

## 8. Ideas for further development

- Other sources with the same pipeline (PulseAudio sink → stream proxy → DMR + eISCP control): e.g. an AirPlay
  receiver (shairport-sync) or a Bluetooth sink on the host.
- A second zone (Zone 2) via the documented eISCP zone-2 commands (`ZPW`, `SLZ`, `ZVL`) – not tested here.
- Using `SetNextAVTransportURI` for gapless metadata refresh (not tested on this renderer).
- Testing other Onkyo/Integra models and documenting differences here.
