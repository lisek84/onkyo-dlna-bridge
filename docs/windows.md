# Windows (experimental, untested)

The container needs **host networking on the real LAN**: Spotify Connect discovery is mDNS multicast, and
the receiver must open a TCP connection back to the host. Plain **Docker Desktop** and **Podman Desktop**
run containers inside a NAT-ed VM, so `network_mode: host` gives the VM's network, not your LAN —
**that setup will not work.**

The only realistic way on Windows is **WSL2 with mirrored networking** and a container engine running
*inside* the WSL distribution:

1. Windows 11 22H2+ with a recent WSL (`wsl --update`).
2. Create `%UserProfile%\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   then `wsl --shutdown`.
3. In an Ubuntu WSL distribution install Docker Engine (`curl -fsSL https://get.docker.com | sh`) or Podman.
   Do **not** use the Docker Desktop WSL integration.
4. Allow inbound traffic into WSL (Hyper-V firewall), in an elevated PowerShell:
   ```powershell
   Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
   ```
   and allow TCP 5901 and UDP 5353 in Windows Defender Firewall for your LAN.
5. Follow [linux.md](linux.md) inside WSL; set `HOST_IP` to the Windows PC's LAN IP.

Caveats: the PC must stay on, mirrored-mode multicast support depends on the WSL version, and this path has
not been tested. A Raspberry Pi or a NAS is a much better host for an always-on audio bridge.
