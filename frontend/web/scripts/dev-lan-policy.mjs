import net from 'node:net';
export function isPrivateDevHost(host) {
 if (host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host === '::1') return true;
 if(net.isIP(host)!==4)return false;
 const [a,b]=host.split('.').map(Number);
 return a===10 || (a===172 && b>=16 && b<=31) || (a===192 && b===168);
}
// Optional private HTTPS dev name (Tailscale Serve). Exact tailnet DNS name only, off unless configured.
const TAILNET_NAME=/^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.){2,}ts\.net$/;
export function normalizePublicHost(value) {
 if(typeof value!=='string')return null;
 const name=value.trim().toLowerCase();
 return TAILNET_NAME.test(name)?name:null;
}
export function forwardedProto(host, options={}) {
 const publicHost=normalizePublicHost(options.publicHost);
 return publicHost && String(host||'').toLowerCase()===publicHost?'https':'http';
}
export function allowedRequest(host, origin, options={}) {
 try {
  const url=new URL(`http://${host}`);
  const publicHost=normalizePublicHost(options.publicHost);
  if(publicHost && url.hostname===publicHost && !url.username && !url.password && url.pathname==='/' && url.port===''){
   if(!origin)return true;
   const source=new URL(origin);
   return source.protocol==='https:' && source.hostname===publicHost && source.port==='';
  }
  if(url.username || url.password || url.pathname!=='/' || !isPrivateDevHost(url.hostname))return false;
  if(!origin)return true;
  const source=new URL(origin);
  return ['http:','https:'].includes(source.protocol) && source.host===url.host;
 } catch {return false;}
}
