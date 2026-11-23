# Queued remove and socket recovery incident

November23,2026. Owner logs show healthy API/worker, response socket disconnected and no later reconnect, no cart-remove handler invocation. Browser explicitly showed queued/unconfirmed. That supports a transport-stranded request, not a server-side removal failure.

## Confirmed source gaps

The opportunistic reconnect read a normally HttpOnly NextAuth session cookie instead of the API access token retained by connectSocket. The socket close handler did not reconnect. A ticket or WebSocket handshake could stay in connecting state without a deadline. Queue flush launched every command concurrently, risking add/remove ordering.

## Additive fix

Stored access-token reconnect with fresh ticket per attempt. Backoff1/2/4/8/15seconds, five retries after the initial attempt; denied401/403 ticket requests do not retry. Ticket request and socket handshake have10second deadlines. Explicit disconnect/signout cancels timers and invalidates callbacks, including pending handshakes. Existing command endpoints and server mutation logic remain unchanged.

Only unsent queue entries are flushed sequentially. A drop leaves the unsent tail queued; submitted uncertain commands are not replayed automatically. Cart UI remains dependent on authoritative cart state, not optimistic fake removal. No customer data or saved cart is deleted by this patch.

Safe server diagnostics now record ordering.socket_closed with user ID, opaque short connection ID, numeric close code and duration_ms. No ticket, raw message or arbitrary close reason. Browser socketError retains numeric close code.

## Original drop remains unresolved

Dev Compose uvicorn uses20second ping interval and20second timeout. A40second connection is consistent with that timeout but does not prove it;5seconds is not explained by it. No5second idle close exists in this route. Need close codes and proxy/browser evidence to distinguish reload/navigation, browser backgrounding, lost network, proxy forwarding and missed pong. Raising timeouts or sending model requests is not a diagnosis.

## Tests

Six actual store/WebSocket event contract tests: queued remove uses stored access token, fresh tickets on reconnect, disconnect cleanup, sequential flush preserving unsent tail, bounded retries/auth denial, handshake timeout. These use controlled browser transport, not a real iPhone/proxy/network test. Full backend disposableSQL/realRedis1139pass4skip; full web30suites166pass and TypeScript passed. No providers, spending, owner-machine deployment/migration or data deletion.
