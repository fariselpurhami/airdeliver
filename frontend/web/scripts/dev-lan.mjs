// Development-only LAN gateway. Production continues to use the existing server.
import http from 'node:http';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {allowedRequest,forwardedProto} from './dev-lan-policy.mjs';
if(process.env.NODE_ENV==='production')throw new Error('LAN gateway is development-only');
const port=Number(process.env.PORT||3000), internal=Number(process.env.DEV_INTERNAL_PORT||3001);
const policy={publicHost:process.env.DEV_PUBLIC_HOST};
const backend=new URL(process.env.BACKEND_API_URL||'http://api:8000');
if(backend.protocol!=='http:')throw new Error('Development API must use internal HTTP');
const require=createRequire(import.meta.url);
const env={...process.env,NODE_ENV:'development',NEXT_PUBLIC_API_URL:'/api/v1',NEXT_PUBLIC_DEV_LAN:'true',AUTH_TRUST_HOST:'true',DEV_LAN_GATEWAY:'true'};
// Auth.js otherwise replaces the requested LAN origin with a fixed loopback URL.
env.AUTH_URL='';env.NEXTAUTH_URL='';env.NEXT_PUBLIC_WS_URL='';env.NEXT_PUBLIC_SOCKET_URL='';
const child=spawn(process.execPath,[require.resolve('next/dist/bin/next'),'dev','--hostname','127.0.0.1','--port',String(internal)],{stdio:'inherit',env});
function target(req){return req.url==='/api/v1'||req.url.startsWith('/api/v1/')||req.url.startsWith('/static/')?{host:backend.hostname,port:Number(backend.port||80),api:true}:{host:'127.0.0.1',port:internal,api:false};}
function headers(req,t){
 const h={...req.headers};delete h['x-forwarded-host'];delete h['x-forwarded-proto'];delete h['x-forwarded-for'];
 h.host=req.headers.host;h['x-forwarded-host']=req.headers.host;h['x-forwarded-proto']=forwardedProto(req.headers.host,policy);
 if(!t.api && (req.url.startsWith('/_next/') || req.url.startsWith('/__nextjs')) && h.origin)h.origin=`http://127.0.0.1:${internal}`;
 return h;
}
const server=http.createServer((req,res)=>{
 if(!allowedRequest(req.headers.host,req.headers.origin,policy)){res.writeHead(403);res.end('Private LAN development origin required');return;}
 const t=target(req);const upstream=http.request({...t,method:req.method,path:req.url,headers:headers(req,t)},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res);});
 upstream.setTimeout(120000,()=>upstream.destroy());
 upstream.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end('Development service starting or unavailable');});req.pipe(upstream);req.on('aborted',()=>upstream.destroy());
});
server.on('upgrade',(req,socket,head)=>{
 if(!allowedRequest(req.headers.host,req.headers.origin,policy)){socket.end('HTTP/1.1 403 Forbidden\r\n\r\n');return;}
 const t=target(req);const upstream=net.connect(t.port,t.host,()=>{
  const h=headers(req,t);upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n`+Object.entries(h).map(([k,v])=>`${k}: ${v}`).join('\r\n')+'\r\n\r\n');if(head.length)upstream.write(head);socket.pipe(upstream).pipe(socket);
 });upstream.on('error',()=>socket.destroy());socket.on('error',()=>upstream.destroy());socket.on('close',()=>upstream.destroy());
});
server.headersTimeout=30000;server.requestTimeout=120000;
server.listen(port,'0.0.0.0',()=>console.log(`LAN dev on port ${port}; localhost and RFC1918 IPv4 only. Open this Mac's current LAN IP.`));
let stopping=false;function stop(){if(stopping)return;stopping=true;server.close();child.kill('SIGTERM');setTimeout(()=>process.exit(),500).unref();}
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,stop);child.on('exit',(code,signal)=>{server.close();if(!stopping){console.error(`Next dev exited: code=${code} signal=${signal}`);process.exit(code||1);}});
child.on('error',(error)=>{console.error('Next dev failed to start:',error.message);server.close();process.exit(1);});
