#!/bin/bash

set -e

if ! command -v nodemon &> /dev/null; then
    echo "ERROR: 'nodemon' is required. Run 'npm install -g nodemon' on your host."
    exit 1
fi

WATCH_PATHS=(
    "docker-compose.dev.yml"
    "./apps/web/package.json"
    "./apps/web/pnpm-lock.yaml"
    "./apps/web/Dockerfile"
    "./apps/web/entrypoint.sh"
    "./apps/api/pyproject.toml"
    "./apps/api/Dockerfile"
    "./apps/c2-gateway/Dockerfile"
    "./apps/drone_client/Dockerfile"
)

WATCH_STRING=$(IFS=','; echo "${WATCH_PATHS[*]}")

nodemon \
    --watch "$WATCH_STRING" \
    --delay 3 \
    --exec 'bash -c "
        echo \"\n\n🚀 ARCHITECTURAL CHANGE DETECTED: REBUILDING...\"
        docker compose -f docker-compose.dev.yml -p airdeliver_dev up -d --build --force-recreate
        docker compose -f docker-compose.dev.yml -p airdeliver_dev logs -f web
        echo \"\n✅ BUILD COMPLETE. WAITING FOR CHANGES...\"
    "' \
    --ext "yml,yaml,json,py,ts,sh" \
    --ignore "**/node_modules"

# dev-auto-watch.sh
