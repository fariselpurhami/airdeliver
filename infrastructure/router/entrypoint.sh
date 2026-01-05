#!/bin/bash
set -eou pipefail

readonly TARGET_HOST="127.0.0.1"
readonly TARGET_PORT="14550"
readonly OUT_HOST="host.docker.internal"
readonly OUT_PORT="14540"
readonly MAX_RETRIES=60 

log() {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') [ROUTER] $1"
}

log "🚀 Initializing airdeliver Network Sidecar..."

if ! command -v mavproxy.py &> /dev/null; then
    log "❌ Critical: mavproxy.py not found in PATH."
    exit 1
fi

retry_count=0
while ! nc -z -u -w 1 "$TARGET_HOST" "$TARGET_PORT"; do
    retry_count=$((retry_count+1))
    if [ "$retry_count" -ge "$MAX_RETRIES" ]; then
        log "💀 Timeout: PX4 Flight Controller at $TARGET_HOST:$TARGET_PORT is unreachable."
        exit 1
    fi
    
    if [ $((retry_count % 5)) -eq 0 ]; then
        log "⏳ Waiting for PX4 UDP stream... ($retry_count/$MAX_RETRIES)"
    fi
    sleep 2
done

log "✅ Connection Established: PX4 is ONLINE."

log "🔌 Bridging Telemetry: $TARGET_HOST:$TARGET_PORT -> $OUT_HOST:$OUT_PORT"

exec mavproxy.py \
    --master="udp:$TARGET_HOST:$TARGET_PORT" \
    --out="udp:$OUT_HOST:$OUT_PORT" \
    --non-interactive \
    --state-basedir=/tmp \
    --daemon
    --default-modules="log,signing,wp,rally,fence,param,tune,apm" 
