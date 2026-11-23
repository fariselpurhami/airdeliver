import net from 'node:net';
export function isPrivateDevHost(host) {
 if (host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host === '::1') return true;
 if(net.isIP(host)!==4)return false;
 const [a,b]=host.split('.').map(Number);
 return a===10 || (a===172 && b>=16 && b<=31) || (a===192 && b===168);
}
export function allowedRequest(host, origin) {
 try {
  const url=new URL(`http://${host}`);
  if(url.username || url.password || url.pathname!=='/' || !isPrivateDevHost(url.hostname))return false;
  if(!origin)return true;
  const source=new URL(origin);
  return ['http:','https:'].includes(source.protocol) && source.host===url.host;
 } catch {return false;}
}
