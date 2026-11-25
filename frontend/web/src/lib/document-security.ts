// A fresh server-generated nonce is forwarded to Next's document renderer.
// Style attributes remain allowed for the existing motion/Three.js UI.
export function documentPolicy(nonce: string, development: boolean): string {
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    `connect-src 'self' https:${development ? ' http: ws: wss:' : ' wss:'}`,
    "media-src 'self' blob: https:",
    "worker-src 'self' blob:",
    "frame-src https://js.stripe.com https://hooks.stripe.com https://www.paypal.com https://www.sandbox.paypal.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self' https://www.paypal.com https://www.sandbox.paypal.com",
    "frame-ancestors 'none'",
  ];
  return directives.join('; ');
}
