#!/bin/bash
# ==============================================================================
# ARCHITECT-GRADE PX4 ENTRYPOINT (TCP EDITION)
# ==============================================================================
set -euo pipefail

readonly SOURCE_DIR="/root/PX4-Autopilot"
readonly CACHE_DIR="/opt/px4-source-cache"
readonly PX4_INTERNAL_PORT=14580

log_info() { echo -e "$(date +'%T') \033[1;34m[ARCHITECT]\033[0m $1"; }

if [ -z "$(ls -A "$SOURCE_DIR" 2>/dev/null)" ]; then
    log_info "Hydrating workspace..."
    cp -ar "$CACHE_DIR/." "$SOURCE_DIR"
fi

setup_bridge() {
    log_info "Initializing TCP Bridge..."
    # TCP4-LISTEN: Reliable, connection-oriented.
    # fork: Handles multiple clients.
    # UDP4: Forwards to PX4 (Internal).
    socat -d -d \
        TCP4-LISTEN:14540,bind=0.0.0.0,fork,reuseaddr \
        UDP4:127.0.0.1:$PX4_INTERNAL_PORT &
    log_info "🔒 TCP Bridge Active: 0.0.0.0:14540 -> Local:14580"
}

main() {
    setup_bridge
    export PX4_SIM_MODEL=${PX4_SIM_MODEL:-gazebo-classic_iris}
    export PX4_SIM_HOSTNAME="localhost"
    log_info "🚀 SYSTEM START: $PX4_SIM_MODEL"
    cd "$SOURCE_DIR"
    exec make px4_sitl "$PX4_SIM_MODEL"
}

main "$@"
