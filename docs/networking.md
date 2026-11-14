# Networking & firewall

The container uses **host networking** (`network_mode: host`). Bridge networking with port mappings does
**not** work: Spotify Connect discovery uses mDNS multicast, and the receiver must connect back to the
host's real LAN address.

## Connections that must be allowed

| Direction | Protocol / port | Purpose |
|---|---|---|
| **receiver → host** | **TCP `STREAM_PORT` (default 5901)** | The receiver pulls the audio stream. **Required — open it in the host firewall for the receiver's IP.** |
| phone/PC → host | UDP 5353 (mDNS) + Soloist's dynamic TCP port | Spotify app discovers and connects to the Soloist device. |
| host → receiver | TCP 8888 (UPnP control/description, Onkyo), UDP 1900 (SSDP) | Starting playback, metadata, state. |
| host → receiver | TCP 60128 (eISCP) | Power, input selection, remote events (`ONKYO_EISCP=yes`). |
| host → internet | HTTPS | Spotify streaming and the Soloist download from `soloist-builds.spotifycdn.com`. |

> **The #1 setup error:** the host firewall silently drops the receiver's connection to TCP 5901.
> The receiver then answers every play request with UPnP error **705 "Transport is locked"** (its generic
> "I could not open the stream" error), nothing plays, and the stream never shows up in the log
> (`[proxy] <receiver-ip> GET /stream.lpcm` lines are missing).
> Testing from your PC proves nothing — the rule must allow the **receiver's** IP.

## Firewall recipes

**Synology DSM** (only if the DSM firewall is enabled) – Control Panel → Security → Firewall →
Edit Rules → Create:
- Ports: **Custom** → Protocol **TCP**, port **5901** (your `STREAM_PORT`)
- Source IP: **Specific IP** → the receiver's IP (or your LAN subnet, e.g. `192.168.1.0/24`)
- Action: **Allow**

Move the rule above any "Deny" rule. Also allow mDNS/Bonjour (UDP 5353) from the LAN, or simply allow
your whole LAN subnet.

**ufw (Ubuntu, Raspberry Pi OS)**
```bash
sudo ufw allow from 192.168.1.50 to any port 5901 proto tcp     # receiver IP
sudo ufw allow from 192.168.1.0/24 to any port 5353 proto udp   # mDNS from the LAN
```
Soloist also listens on a dynamic TCP port for the Spotify app. With a restrictive firewall, allow your LAN
subnet to the host (`sudo ufw allow from 192.168.1.0/24`).

**firewalld (Fedora, RHEL, openSUSE)**
```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=192.168.1.50 port port=5901 protocol=tcp accept'
sudo firewall-cmd --permanent --add-service=mdns
sudo firewall-cmd --reload
```

## Several network interfaces

If the host has VPN, Docker bridges, a second NIC etc., set `HOST_IP` explicitly to the LAN address the
receiver can reach. The auto-detection picks the interface used to route to `RENDERER_IP`, which is
usually correct.

## Quick checks

```bash
# from the host: is the receiver's DLNA renderer reachable?
curl -s http://<receiver-ip>:8888/upnp_descriptor_0 | head -c 300
# from another LAN machine while Spotify is playing: is the stream served?
curl -s -o /dev/null -w '%{http_code}\n' -r 0-1023 http://<host-ip>:5901/stream.lpcm   # expect 206
```
