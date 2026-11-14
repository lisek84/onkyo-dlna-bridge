# onkyo-spotify-connect - x86_64 (amd64) image
#   Spotify Soloist (official Spotify Connect receiver) -> PulseAudio null sink
#   -> swyh-rs-cli -> HTTP proxy -> DLNA renderer of a network receiver (LPCM 44.1 kHz / 16 bit)
#
# Spotify Soloist is NOT included in this image: Spotify does not allow redistributing
# its binaries. The container downloads the current build from Spotify's CDN on start
# (builds expire after 90 days - a container restart fetches a fresh one).
#
# For ARM (Raspberry Pi) use Dockerfile.arm - swyh-rs has no ARM CLI release.
#
# Third-party software in this image: swyh-rs-cli (MIT, license in /usr/share/doc/swyh-rs/LICENSE)
# and Debian packages (licenses in /usr/share/doc/<package>/copyright).

FROM debian:trixie-slim

ARG SWYH_VERSION=1.21.1

LABEL org.opencontainers.image.title="onkyo-spotify-connect" \
      org.opencontainers.image.description="Spotify Connect for legacy Onkyo network receivers via Spotify Soloist and DLNA" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Lisek (lisek84)" \
      org.opencontainers.image.source="https://github.com/lisek84/onkyo-spotify-connect"

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl tini procps python3 \
      pulseaudio pulseaudio-utils libpulse0 \
      libasound2t64 libasound2-plugins \
 && rm -rf /var/lib/apt/lists/*

# swyh-rs-cli is released only as an AppImage - unpack it (containers have no FUSE).
RUN mkdir -p /opt/swyh && cd /opt/swyh \
 && curl -fsSL -o swyh.AppImage \
      "https://github.com/dheijl/swyh-rs/releases/download/${SWYH_VERSION}/swyh-rs-cli-x86_64.AppImage" \
 && chmod +x swyh.AppImage \
 && ./swyh.AppImage --appimage-extract >/dev/null \
 && install -m 755 squashfs-root/usr/bin/swyh-rs-cli /usr/local/bin/swyh-rs-cli \
 && rm -rf /opt/swyh \
 && mkdir -p /usr/share/doc/swyh-rs \
 && curl -fsSL -o /usr/share/doc/swyh-rs/LICENSE \
      "https://raw.githubusercontent.com/dheijl/swyh-rs/${SWYH_VERSION}/LICENSE"

COPY pulse.pa    /etc/pulse/soloist.pa
COPY asound.conf /etc/asound.conf
COPY entrypoint.sh dlna-proxy.py amp-ctl.py now-meta.py iscp-events.py /usr/local/bin/
RUN chmod 755 /usr/local/bin/entrypoint.sh /usr/local/bin/dlna-proxy.py /usr/local/bin/amp-ctl.py \
              /usr/local/bin/now-meta.py /usr/local/bin/iscp-events.py

VOLUME ["/config"]
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
