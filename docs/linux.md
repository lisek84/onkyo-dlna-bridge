# Linux, Raspberry Pi, Podman

Any Linux host in the same LAN as the receiver: a mini PC, a home server, a Raspberry Pi, a VM with a
**bridged** network adapter (not NAT). The host needs Docker (with the compose plugin) or Podman.

## Docker (x86_64)

```bash
git clone https://github.com/lisek84/onkyo-spotify-connect.git
cd onkyo-spotify-connect
cp soloist.env.example soloist.env && nano soloist.env
docker compose up -d --build
docker compose logs -f
```

Set `PUID`/`PGID` to the user that should own `./config` (`id -u`, `id -g`).
Open the firewall for the receiver → host TCP 5901: [networking.md](networking.md).

## Raspberry Pi (arm64 / armv7) — untested

Soloist officially supports Raspberry Pi (arm64 and arm32). swyh-rs has no ARM release, so
`image/Dockerfile.arm` compiles it from source.

1. Raspberry Pi OS **64-bit** (Bookworm/Trixie) recommended; Pi 3 or newer. Wired Ethernet recommended.
2. Install Docker: `curl -fsSL https://get.docker.com | sh` and `sudo usermod -aG docker $USER` (log in again).
3. Make sure there is enough memory for the Rust build (≥ 2 GB RAM+swap). On 1 GB models increase swap,
   e.g. set `CONF_SWAPSIZE=2048` in `/etc/dphys-swapfile` and restart `dphys-swapfile`.
4. Edit `compose.yaml`: `dockerfile: Dockerfile.arm`
5. `docker compose up -d --build` — the first build can take 20–60+ minutes on a Pi; later builds are cached.

Alternatively build on a faster machine with buildx (`--platform linux/arm64`) and copy the image.

## Podman

`compose.yaml` works with **podman-compose** or `podman compose`:

```bash
podman compose up -d --build
```

Rootless Podman works with host networking, but binding mDNS and receiving multicast can be restricted by
the host; if the device does not appear in Spotify, try rootful (`sudo podman …`).

### Podman Quadlet (systemd service)

`deploy/podman/onkyo-spotify-connect.container` is a Quadlet unit:

```bash
sudo mkdir -p /opt/onkyo-spotify-connect/config
sudo cp soloist.env /opt/onkyo-spotify-connect/
sudo podman build -t localhost/onkyo-spotify-connect:latest -f image/Dockerfile image   # Dockerfile.arm on ARM
sudo cp deploy/podman/onkyo-spotify-connect.container /etc/containers/systemd/
sudo systemctl daemon-reload
sudo systemctl start onkyo-spotify-connect
journalctl -u onkyo-spotify-connect -f
```

On SELinux systems the `:Z` volume option relabels the config directory.

## Running without containers

Possible but not packaged: install PulseAudio, Python 3, swyh-rs-cli and Soloist on a glibc ≥ 2.38 system
and run `image/entrypoint.sh` as root with the same environment variables and a writable `/config`.
The container is the supported path.
