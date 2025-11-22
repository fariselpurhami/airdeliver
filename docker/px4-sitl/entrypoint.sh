#!/bin/bash

set -e

SOURCE_DIR="/root/PX4-Autopilot"
CACHE_DIR="/opt/px4-source-cache"

if [ -z "$(ls -A $SOURCE_DIR)" ]; then
    cp -ar $CACHE_DIR/. $SOURCE_DIR
fi

if [ -n "$PX4_SIM_MODEL" ]; then
    export PX4_SIM_MODEL=${PX4_SIM_MODEL}
fi

export MAVLINK_UDP_HOST=${MAVLINK_UDP_HOST:-127.0.0.1}
export MAVLINK_UDP_PORT=${MAVLINK_UDP_PORT:-14540}

exec "$@"

# airdeliver/docker/px4-sitl
