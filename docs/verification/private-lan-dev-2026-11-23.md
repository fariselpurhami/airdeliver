# Private LAN development access

The combined base+dev Compose web command now starts a development-only gateway on 0.0.0.0:3000. Next itself listens on loopback:3001. Production commands and backend CORS are unchanged. Existing package `dev` remains; `dev:lan` is additive.

The gateway allows localhost, loopback and RFC1918 IPv4 hostnames only. Supplied Origin must exactly match host and port. It strips incoming forwarded-host/protocol values and supplies checked values. API HTTP/WebSocket and backend `/static/` use the same browser origin. Next HMR is forwarded only after this check, without wildcard dev origins. Auth.js request callbacks retain the checked external origin only under the development gateway flag. Runtime ignores stale loopback AUTH_URL, API and socket settings for this flow.

Verified locally through the machine's private interface: HTML 200, API proxy 200, dynamic 192.168 and 10-range Host/Origin pairs 200, public host and hostile Origin 403, Auth.js providers and CSRF 200, callbacks retained current Host after address change, HMR upgrade 101. Browser mobile home inspected through private-interface HTTP. API smoke used a local fixture, not the owner's backend. No actual sign-in or owner-phone request proven. Policy tests cover boundaries and hostname tricks; full frontend tests, TypeScript and production build run separately. No production CORS relaxation, firewall or router edit, database write, provider call or deployment.

## Owner steps, only after approval/merge

1. Pull main in the existing repo.
2. Recreate only web, preserving the held migration and avoiding dependencies:
   `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps web`
3. Open `http://192.168.1.2:3000` from another device on the same trusted Wi-Fi. If the Mac changes IP, open its new IP. API, auth and socket URLs follow that origin without editing config.
4. Check the Mac's current Wi-Fi IPv4 in System Settings > Wi-Fi > Details > TCP/IP. An already-open tab at a dead IP cannot discover a new IP automatically.
5. If macOS prompts about Docker incoming connections, allow Docker Desktop. If access is blocked, System Settings > Network > Firewall > Options, allow Docker Desktop incoming connections. Do not disable the firewall or enable router port forwarding. Docker Desktop must be running and the devices must not be isolated by guest Wi-Fi/client isolation.

A stable Bonjour `.local` hostname would avoid remembering changing IPs, but it is not enabled by this IP-only policy. HTTP LAN is not a secure context: microphone, camera and service-worker/PWA installation are not promised. Existing mobile installation gate stays unchanged, so browser mobile deep links can redirect home. Trusted HTTPS and stable hostname support need separate scope rather than silently weakening these policies. Any current session cookies belong to their original host; sign in again on a changed IP.

Documentation checked: https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins and https://nextjs.org/docs/app/guides/custom-server . The gateway preserves the normal Next development process and does not alter the standalone production server.
