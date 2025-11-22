#!/bin/sh
# السماح بمحاولات الإصلاح دون توقف فوري
set +e

echo "🛡️ [Self-Healing] Starting architectural integrity check..."


if [ -d ".next" ]; then
    echo "🔥 [Self-Healing] Refreshing build cache..."
    find .next -mindepth 1 -delete
fi


if [ -d "node_modules/next-pwa" ]; then
    echo "🚨 [Self-Healing] Removing legacy artifact 'next-pwa'..."
    rm -rf node_modules
fi


if [ -f "pnpm-workspace.yaml" ]; then
    echo "🗑️ [Self-Healing] Removing conflicting 'pnpm-workspace.yaml'..."
    rm pnpm-workspace.yaml
fi

echo "🔄 [Self-Healing] Syncing dependencies..."


pnpm config set store-dir /root/.pnpm-store


pnpm install --reporter=silent


set -e

echo "✅ [Self-Healing] Ready. Launching application..."
exec "$@"
