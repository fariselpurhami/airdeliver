#!/bin/bash
set -e

export MAVLINK_UDP_HOST=companion
export MAVLINK_UDP_PORT=14540

exec "$@"

# docker/px4-sitl/entrypoint.sh
