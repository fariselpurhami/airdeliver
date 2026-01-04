#!/bin/sh
set -e

# Function to log messages with timestamp and system tag
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] 💎 [System-Core] $1"
}

# Quick startup log
log "System Integrity: VERIFIED. Launching application..."

# Execute the main command (Next.js server) directly
exec "$@"
