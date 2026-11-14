# Synology DSM (Container Manager)

Tested on a DS718+ (x86_64, DSM 7.2, Container Manager). Any **x86_64** Synology with Container Manager
should work. ARM-based Synology models are untested (they would need `Dockerfile.arm` and enough RAM to
compile swyh-rs).

## 1. Prepare the folder

1. Install **Container Manager** from the Package Center (it creates the shared folder `docker`).
2. Create the folder `/volume1/docker/onkyo-spotify-connect` (File Station).
3. Copy into it:
   - `deploy/synology/compose.yaml` → `compose.yaml`
   - the whole `image/` folder → `image/`
   - `soloist.env.example` → `soloist.env`

   Result:
   ```
   /volume1/docker/onkyo-spotify-connect/
   ├── compose.yaml
   ├── soloist.env
   └── image/
       ├── Dockerfile
       ├── entrypoint.sh, dlna-proxy.py, amp-ctl.py, now-meta.py, iscp-events.py
       └── pulse.pa, asound.conf
   ```
4. Edit `soloist.env` (File Station → Open with Text Editor, or via SSH):
   - `SOLOIST_API_KEY` – see [spotify-developer-key.md](spotify-developer-key.md)
   - `RENDERER_IP` – your receiver
   - `DEVICE_NAME` – name in Spotify
   - `PUID` / `PGID` – your DSM user and group (SSH: `id`). Typically the first admin user is `1026` and the
     `users` group is `100`.
   - `HOST_IP` – recommended on Synology: the NAS LAN IP (DSM often has extra interfaces for Docker/VPN).

## 2. Firewall

If the DSM firewall is enabled, allow **TCP 5901 from the receiver's IP** — see
[networking.md](networking.md#firewall-recipes). Without it the receiver cannot fetch the stream and
playback fails with UPnP 705.

## 3. Create the project

Container Manager → **Project** → **Create**:
- Project name: `onkyo-spotify-connect`
- Path: `/docker/onkyo-spotify-connect`
- Source: **Use existing docker-compose.yml** (compose.yaml)
- Skip the web portal settings → **Done**. The image is built (a few minutes) and the container starts.

`pull_policy: build` makes Container Manager rebuild the image on every project start, so updated scripts
are always picked up.

## 4. Check

Container Manager → Container → `onkyo-spotify-connect` → **Log**, or the file
`/volume1/docker/onkyo-spotify-connect/config/container.log`. You should see:

```
[entrypoint] onkyo-spotify-connect 1.0.0
[entrypoint] started: pulseaudio=… soloist=… proxy=… eiscp=… watcher=…
[eiscp] connected to <receiver-ip>:60128
… ready, device_name=… 
```

Then pick the device in the Spotify app and play.

## Updating

Copy the new `image/` folder (and compare `compose.yaml` / `soloist.env.example` for new settings), then
Container Manager → Project → **Stop** → **Build** → **Start**. Your login and settings in `config/` and
`soloist.env` are kept.

## Notes

- The Soloist build is downloaded to `config/bin/` and refreshed automatically when Spotify publishes a newer
  one; an expired build makes the container restart and fetch a new one.
- DSM's own Bonjour service and the container both use mDNS; this works fine with host networking.
