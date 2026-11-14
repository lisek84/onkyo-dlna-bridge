# Receiver setup (Onkyo TX-NR609 and similar)

Do this once, before starting the container.

## 1. Network and a fixed IP

- Connect the receiver to the LAN (Ethernet recommended) and check that NET works (e.g. internet radio).
- Give it a **fixed IP**: a DHCP reservation in your router (by MAC address) is the easiest. The MAC is
  shown in the receiver's web setup page (see below) and in the network setup menu.
  Put this IP into `RENDERER_IP`.
- Enable **Network Standby** (Setup → Hardware/Network Setup → Network Standby = On, wording differs per
  model). Without it the receiver is unreachable in standby and cannot be powered on over the network.

## 2. Web setup page: "DMR Max Volume" and "Auto Play"

Open `http://<receiver-ip>/` in a browser → **Unit information**:

| Setting | Recommended | Why |
|---|---|---|
| **DMR Max Volume (0-100)** | e.g. `60`–`70` | Upper volume limit applied whenever DLNA playback starts. If it is `0`, the volume drops to 0 at every track – the most common "it plays but I hear nothing" cause. |
| **Auto Play** | `Yes` | Lets DLNA playback start the receiver's player. |
| Friendly Name | anything | The DLNA renderer name (not the Spotify device name). |

Press **SAVE**.

## 3. Things to know

- **The receiver must be able to reach the host** on TCP `STREAM_PORT` (default 5901) — see
  [networking.md](networking.md). This is the most common setup error.
- The container switches the receiver to **NET** and opens the **DLNA** service before starting playback,
  exactly like the official *Onkyo Remote* app does. Without that step the 2011 firmware may answer every
  play request with UPnP error 705 "Transport is locked".
- The volume slider in the Spotify app changes the stream level (Soloist digital volume). The amplifier
  volume stays on the remote. `INITIAL_VOLUME` sets the starting stream level.
- If the receiver's DLNA renderer ever hangs completely (no answer on port 8888), only unplugging the
  receiver from mains for ~30 s helps; standby does not restart the network module.
