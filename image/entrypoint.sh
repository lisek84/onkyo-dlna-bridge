#!/bin/bash
# onkyo-dlna-bridge - container entrypoint
#
# Starts PulseAudio (virtual "dlna" sink), Spotify Soloist (Spotify Connect receiver),
# an HTTP proxy for the receiver, an eISCP event listener, and a watcher that:
#   - starts swyh-rs-cli (audio capture -> HTTP stream) while Spotify is playing,
#   - prepares the receiver (power on, NET input, DLNA service) and starts DLNA playback,
#   - pushes track title/artist to the receiver display,
#   - maps the receiver remote: Stop -> pause Spotify, NET -> resume, power off -> pause.
set -euo pipefail

VERSION="1.3.0"

# ---------------------------------------------------------------- configuration --
: "${PUID:=1000}"                       # user/group that owns /config
: "${PGID:=1000}"
: "${DEVICE_NAME:=Onkyo Receiver}"      # name shown in the Spotify app
: "${RENDERER_IP:?set RENDERER_IP to the IP address of your receiver}"
: "${SOLOIST_API_KEY:?set SOLOIST_API_KEY (see docs/spotify-developer-key.md)}"
: "${HOST_IP:=}"                        # LAN IP of this host; auto-detected when empty
: "${INITIAL_VOLUME:=70}"               # initial Soloist (digital) volume 0-100
: "${STREAM_PORT:=5901}"                # TCP port the receiver pulls audio from (open it in the firewall)
: "${STREAM_ALLOW=renderer}"            # who may fetch the audio stream: "renderer" = only RENDERER_IP
                                        # (default), a comma list of IPs/subnets, or empty = anyone in the LAN
: "${SWYH_PORT:=5911}"                  # internal swyh-rs port (read only by the proxy)
: "${PLAY_TITLE:=Spotify}"              # display text when no track metadata is sent
: "${COVER_ART:=yes}"                   # yes = send the album cover with the metadata (shown on the TV/OSD)
: "${COVER_SIZE:=default}"              # cover size from Spotify: default (300 px), large (640 px), small (64 px)
export COVER_SIZE
: "${META_UPDATE:=yes}"                 # yes = show title/artist, refreshed on every track change
: "${ONKYO_EISCP:=yes}"                 # yes = Onkyo/Integra/Pioneer eISCP control (power, input, remote)
: "${AUTO_POWER_ON:=yes}"               # yes = power the receiver on when Spotify starts playing
: "${REMOTE_CONTROL:=yes}"              # yes = remote Stop pauses Spotify, NET resumes, power off pauses
: "${NET_RESUME_SECONDS:=1800}"         # how long after a remote Stop the NET button resumes playback
: "${IDLE_STOP_SECONDS:=300}"           # stop streaming after this long paused
: "${AMP_MAX_TRIES:=3}"                 # start attempts per playback session
: "${LOG_TO_FILE:=yes}"                 # yes = also write /config/container.log (rotated at 5 MB)
: "${SWYH_SOURCE:=Sound Server-pulse}"  # swyh-rs audio source (unique part of its name)
: "${SWYH_EXTRA_ARGS:=}"
: "${SOLOIST_EXTRA_ARGS:=}"
STREAM_SIZE=U64maxNotChunked            # swyh-rs -> proxy only; the receiver sees the proxy headers

log() { echo "[entrypoint] $(date '+%H:%M:%S') $*"; }

if [ "$ONKYO_EISCP" != "yes" ]; then
  AUTO_POWER_ON=no   # power control needs eISCP
fi

# ------------------------------------------------- log to /config/container.log --
if [ "$LOG_TO_FILE" = "yes" ]; then
  LOGF=/config/container.log
  if [ -f "$LOGF" ] && [ "$(stat -c%s "$LOGF")" -gt 5000000 ]; then mv -f "$LOGF" "$LOGF.1"; fi
  exec > >(while IFS= read -r l; do printf '%s %s\n' "$(date '+%F %T')" "$l"; done | tee -a "$LOGF") 2>&1
fi

log "onkyo-dlna-bridge $VERSION"

# ----------------------------------------------------------- host IP detection --
if [ -z "$HOST_IP" ]; then
  HOST_IP=$(python3 -c "import socket,sys; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect((sys.argv[1],9)); print(s.getsockname()[0])" "$RENDERER_IP" 2>/dev/null || true)
  [ -n "$HOST_IP" ] || { log "ERROR: cannot detect HOST_IP - set it explicitly"; exit 1; }
  log "detected HOST_IP=$HOST_IP (route to $RENDERER_IP)"
fi

# ------------------------------------------------- unprivileged runtime user --
# PulseAudio refuses to run as root in user mode.
if ! getent group "$PGID" >/dev/null; then groupadd -g "$PGID" soloist; fi
if ! getent passwd "$PUID" >/dev/null; then
  useradd -u "$PUID" -g "$PGID" -M -d /config/home -s /usr/sbin/nologin soloist
fi
RUN_USER=$(getent passwd "$PUID" | cut -d: -f1)

DATA=/config/soloist-data
mkdir -p /config/home/.swyh-rs /config/bin "$DATA" /config/soloist-cache
export RUNTIME=/tmp/runtime-$PUID
# /tmp survives a container restart - a stale PulseAudio PID file would block startup.
rm -rf "$RUNTIME" /config/home/.config/pulse/*-runtime 2>/dev/null || true
mkdir -p "$RUNTIME"

# ------------------------------------- swyh-rs configuration (rewritten each start) --
cat > /config/home/.swyh-rs/configsoloist.toml <<EOF
[configuration]
server_port = $SWYH_PORT
auto_resume = true
sound_source = "$SWYH_SOURCE"
log_level = "INFO"
ssdp_interval_mins = 10.0
auto_reconnect = true
enable_slimproto = false
lpcm_stream_size = "$STREAM_SIZE"
wav_stream_size = "$STREAM_SIZE"
rf64_stream_size = "U64maxNotChunked"
flac_stream_size = "NoneChunked"
bits_per_sample = 16
streaming_format = "Lpcm"
monitor_rms = false
capture_timeout = 2000
inject_silence = true
buffering_delay_msec = 0
latency_reduction_delay_msec = 0
latency_reduction_msec = 0
last_network = "127.0.0.1"
active_renderers = []
hidden_renderers = []
config_dir = "/config/home/.swyh-rs"
config_id = "soloist"
read_only = false
color_theme = 8
widget_scheme = 1
language = "en-US"
sample_rate = 44100
use_dither = true
EOF

chown -R "$PUID:$PGID" /config "$RUNTIME"
chmod 700 "$RUNTIME" "$DATA"

# ---------------------- download Spotify Soloist from Spotify's CDN (only if newer) --
case "$(uname -m)" in
  x86_64)        SOLOIST_ARCH=x86_64 ;;
  aarch64|arm64) SOLOIST_ARCH=arm64 ;;
  armv7l|armv7*) SOLOIST_ARCH=arm32 ;;
  *) log "ERROR: unsupported architecture $(uname -m)"; exit 1 ;;
esac
SOLOIST=/config/bin/soloist
URL="https://soloist-builds.spotifycdn.com/soloist_release_${SOLOIST_ARCH}.tar.gz"
TMP=$(mktemp -d)
if [ -f /config/bin/soloist.tar.gz ]; then ZFLAG=(-z /config/bin/soloist.tar.gz); else ZFLAG=(); fi
if curl -fsSL "${ZFLAG[@]}" -o "$TMP/soloist.tar.gz" "$URL" && [ -s "$TMP/soloist.tar.gz" ]; then
  tar -xzf "$TMP/soloist.tar.gz" -C "$TMP" soloist
  install -m 755 "$TMP/soloist" "$SOLOIST"
  mv "$TMP/soloist.tar.gz" /config/bin/soloist.tar.gz
  log "downloaded a new Soloist build ($SOLOIST_ARCH)"
elif [ -x "$SOLOIST" ]; then
  log "Soloist is up to date (or the CDN is unreachable) - using the existing build"
else
  log "ERROR: could not download Soloist from $URL"; exit 1
fi
rm -rf "$TMP"
chown "$PUID:$PGID" "$SOLOIST"

as_user() {
  runuser -u "$RUN_USER" -- env HOME=/config/home XDG_RUNTIME_DIR="$RUNTIME" \
    PULSE_SERVER="unix:$RUNTIME/pulse/native" "$@"
}

# ------------------------------------- 1. PulseAudio with a virtual "dlna" output --
as_user pulseaudio -n -F /etc/pulse/soloist.pa --daemonize=no --exit-idle-time=-1 \
  --disallow-exit --log-target=stderr --log-level=error \
  2> >(grep --line-buffered -v 'Failed to connect to system bus' >&2) &
PA_PID=$!
for _ in $(seq 1 50); do as_user pactl info >/dev/null 2>&1 && break; sleep 0.2; done
as_user pactl info | grep -E 'Default (Sink|Source)' || { log "ERROR: PulseAudio did not start"; exit 1; }

# -------------- 2. Soloist: Spotify Connect receiver (+ local WebSocket API for state) --
# shellcheck disable=SC2086
as_user "$SOLOIST" -n "$DEVICE_NAME" -k "$SOLOIST_API_KEY" \
  -D "$DATA" -C /config/soloist-cache -z 500 -w 127.0.0.1:0 \
  -i "$INITIAL_VOLUME" $SOLOIST_EXTRA_ARGS &
SOLOIST_PID=$!

# ---------------------------- 3. stream server, proxy and receiver control helpers --
# swyh-rs captures the PulseAudio monitor and serves it locally (SWYH_PORT).
# dlna-proxy.py serves it to the receiver as a large "file" (Content-Length, Range,
# 206) and sends silence instead of an error while swyh-rs is not running - legacy
# DMRs lock up (UPnP 705) after a failed stream. amp-ctl.py starts playback.
# swyh-rs listens on localhost only (the receiver talks to the proxy, never to swyh-rs);
# the proxy falls back to HOST_IP in case swyh-rs binds there instead.
export RENDERER_IP AUTO_POWER_ON ONKYO_EISCP STREAM_ALLOW PROXY_PORT="$STREAM_PORT" \
       UPSTREAM_HOST="127.0.0.1,$HOST_IP" UPSTREAM_PORT="$SWYH_PORT"
STREAM_URL="http://$HOST_IP:$STREAM_PORT/stream.lpcm"

python3 -u /usr/local/bin/dlna-proxy.py &
PROXY_PID=$!

# Persistent eISCP connection: receiver events (NET button, power off).
rm -f /tmp/iscp-net /tmp/iscp-off /tmp/proxy-eof
ISCP_PID=""
if [ "$ONKYO_EISCP" = "yes" ]; then
  python3 -u /usr/local/bin/iscp-events.py &
  ISCP_PID=$!
fi

amp() { python3 -u /usr/local/bin/amp-ctl.py "$@"; }

SWYH_PID=""
swyh_running() { [ -n "$SWYH_PID" ] && kill -0 "$SWYH_PID" 2>/dev/null; }
swyh_start() {
  # shellcheck disable=SC2086
  as_user swyh-rs-cli -c soloist -x true -e 127.0.0.1 -p "$SWYH_PORT" \
    -s "$SWYH_SOURCE" -f lpcm -b 16 -R 44100 -S true -P false \
    $SWYH_EXTRA_ARGS 2>&1 | grep --line-buffered -vE 'ALSA lib|Jack|jack server|Cannot connect to server' &
  SWYH_PID=$!
  log "capture started (swyh-rs pid $SWYH_PID), stream: $STREAM_URL"
}
swyh_stop() {
  if swyh_running; then
    pkill -TERM -u "$PUID" -f swyh-rs-cli 2>/dev/null || true
    wait "$SWYH_PID" 2>/dev/null || true
    log "capture stopped"
  fi
  SWYH_PID=""
}

sctl() { as_user "$SOLOIST" ctl -D "$DATA" "$@" >/dev/null 2>&1; }

# ------------------------------------------------------------------- watcher --
watcher() {
  set +e
  local status last="" idle_since now next_amp=0 tries=0 st ast ours json title artist album cover
  local meta="" shown="" amp_prev="" user_stop=0 stop_ts=0 net_ts play_seen=0
  local off_ts off_seen=0 off_hold=0 net_used=0 eof_ts
  idle_since=$(date +%s)
  while kill -0 "$SOLOIST_PID" 2>/dev/null; do
    json=$(as_user "$SOLOIST" ctl -D "$DATA" now --json 2>/dev/null)
    IFS=$'\x1f' read -r status title artist album cover < <(printf '%s' "$json" | python3 /usr/local/bin/now-meta.py)
    status=${status:-idle}
    [ "$META_UPDATE" = "yes" ] || { title=""; artist=""; album=""; cover=""; }
    [ "$COVER_ART" = "yes" ] || cover=""
    meta="$title|$artist"
    if [ "$status" != "$last" ]; then
      log "Soloist: $status"
      case "$status" in playing|buffering)
        case "$last" in playing|buffering) ;; *) tries=0; user_stop=0 ;; esac ;;   # new playback session
      esac
      last=$status
    fi
    now=$(date +%s)

    # --- receiver switched off by the user -> pause Spotify, never power it back on ---
    if [ -f /tmp/iscp-off ]; then
      off_ts=$(cut -d. -f1 /tmp/iscp-off 2>/dev/null)
      if [ -n "$off_ts" ] && [ "$off_ts" -gt "$off_seen" ]; then
        off_seen=$off_ts
        if [ "$REMOTE_CONTROL" = "yes" ] && { swyh_running || [ "$status" = "playing" ]; }; then
          log "receiver switched off -> pausing Spotify"
          [ "$status" = "playing" ] && sctl pause
          user_stop=1; stop_ts=$play_seen; status=paused; last=paused; idle_since=$now
          off_hold=$((now + 15))
        fi
      fi
    fi
    # Spotify sometimes "bounces" a pause and resumes by itself right after it.
    if [ "$status" = "playing" ] && [ "$now" -lt "$off_hold" ]; then
      log "Spotify resumed by itself right after Stop/power off -> pausing again"
      sctl pause; status=paused; last=paused; user_stop=1
    fi

    # --- receiver DMR state (every 2 s while streaming) ---
    st=""
    if swyh_running && [ "$now" -ge "$next_amp" ]; then
      st=$(amp state 2>/dev/null); next_amp=$((now + 2))
    fi
    ast=${st%% http*}
    ours=0; case "$st" in *"$STREAM_URL"*) ours=1 ;; esac

    # --- remote Stop on the receiver -> pause Spotify ---
    if [ -n "$st" ] && [ "$REMOTE_CONTROL" = "yes" ] && [ "$ours" = 1 ]; then
      eof_ts=$(cut -d. -f1 /tmp/proxy-eof 2>/dev/null || echo 0)
      if [ "$amp_prev" = "PLAYING OK" ] && [ "$ast" = "STOPPED OK" ] && [ "$status" = "playing" ] \
         && [ $((now - ${eof_ts:-0})) -lt 60 ]; then
        log "end of the ~3 h stream reached -> restarting the stream"
        amp_prev=""; tries=0
      elif [ "$amp_prev" = "PLAYING OK" ] && [ "$ast" = "STOPPED OK" ] && [ "$status" = "playing" ]; then
        log "remote: Stop -> pausing Spotify"
        # NET counts from the last moment the receiver was still playing (Stop is detected up to 2 s late)
        sctl pause; user_stop=1; stop_ts=$play_seen; status=paused; last=paused; idle_since=$now
        off_hold=$((now + 6))
      fi
    fi
    [ -n "$st" ] && amp_prev=$ast
    [ "$ast" = "PLAYING OK" ] && play_seen=$now

    # --- NET button after a remote Stop / power off -> resume Spotify ---
    if [ "$REMOTE_CONTROL" = "yes" ] && [ "$user_stop" = 1 ] && [ -f /tmp/iscp-net ]; then
      net_ts=$(cut -d. -f1 /tmp/iscp-net 2>/dev/null)
      if [ -n "$net_ts" ] && [ "$net_ts" -ge "$stop_ts" ] && [ "$net_ts" -gt "$net_used" ] \
         && [ $((now - stop_ts)) -lt "$NET_RESUME_SECONDS" ]; then
        log "remote: NET -> resuming Spotify"
        sctl play; user_stop=0; off_hold=0; net_used=$net_ts
      fi
    fi

    case "$status" in
      playing|buffering)
        idle_since=$now
        if ! swyh_running; then swyh_start; next_amp=$((now + 3)); fi
        if [ -n "$st" ]; then
          case "$st" in
            "PLAYING "*"$STREAM_URL"*)                            # our stream is playing
              if [ "$META_UPDATE" = "yes" ] && [ -n "$title" ] && [ "$meta" != "$shown" ]; then
                log "new track: $title - $artist (updating the display)"
                amp play "$STREAM_URL" "$title" "${artist:-$PLAY_TITLE}" "$album" "$cover" && { shown=$meta; amp_prev="PLAYING OK"; }
                next_amp=$(( $(date +%s) + 2 ))
              fi ;;
            "PLAYING "*) ;;                                      # something else is playing - leave it
            *)
              if [ "$user_stop" = 0 ] && [ "$tries" -lt "$AMP_MAX_TRIES" ]; then
                tries=$((tries + 1))
                log "receiver: '${st:-?}' -> starting playback (attempt $tries/$AMP_MAX_TRIES)"
                # wait until swyh-rs listens (max 10 s)
                for _ in $(seq 1 20); do
                  { (exec 3<>"/dev/tcp/127.0.0.1/$SWYH_PORT") || (exec 3<>"/dev/tcp/$HOST_IP/$SWYH_PORT"); } 2>/dev/null && break
                  sleep 0.5
                done
                # amp-ctl verifies PLAYING, so treat it as playing at once - a remote Stop
                # right after the start must not look like a failure
                if amp play "$STREAM_URL" "${title:-$PLAY_TITLE}" "${artist:-$PLAY_TITLE}" "$album" "$cover"; then
                  shown=$meta; amp_prev="PLAYING OK"; play_seen=$(date +%s)
                else
                  amp_prev=""
                fi
                next_amp=$(( $(date +%s) + 2 ))
              fi ;;
          esac
        fi ;;
      *)
        if swyh_running && [ $((now - idle_since)) -ge "$IDLE_STOP_SECONDS" ]; then
          amp stop "$STREAM_URL"
          swyh_stop
        fi ;;
    esac
    sleep 2
  done
}
watcher &
WATCH_PID=$!

log "started: pulseaudio=$PA_PID soloist=$SOLOIST_PID proxy=$PROXY_PID eiscp=${ISCP_PID:-off} watcher=$WATCH_PID"
log "receiver=$RENDERER_IP host=$HOST_IP stream=$STREAM_URL eiscp=$ONKYO_EISCP auto_power_on=$AUTO_POWER_ON remote=$REMOTE_CONTROL metadata=$META_UPDATE cover=$COVER_ART/$COVER_SIZE stream_allow=${STREAM_ALLOW:-anyone}"

# If PulseAudio, Soloist or the proxy exits, exit too and let the restart policy restart
# the container (this also fetches a fresh Soloist build after expiry, exit code 10).
set +e
wait -n "$PA_PID" "$SOLOIST_PID" "$PROXY_PID"
RC=$?
log "PulseAudio/Soloist/proxy exited (code $RC) - exiting so the container is restarted"
kill "$WATCH_PID" "$PROXY_PID" ${ISCP_PID:+"$ISCP_PID"} 2>/dev/null; pkill -TERM -f swyh-rs-cli 2>/dev/null; kill "$PA_PID" "$SOLOIST_PID" 2>/dev/null
exit "$RC"
