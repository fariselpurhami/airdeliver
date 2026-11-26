import {test} from 'node:test';
import assert from 'node:assert/strict';
import {allowedRequest,isPrivateDevHost} from './dev-lan-policy.mjs';
test('loopback and all RFC1918 ranges, including a changed network',()=>{
 for(const h of ['localhost','127.0.0.1','[::1]','192.168.1.2','192.168.50.99','10.0.0.1','172.16.0.1','172.31.255.255'])assert.equal(isPrivateDevHost(h),true,h);
});
test('no public, link local, hostname wildcard or encoded-IP bypass',()=>{
 for(const h of ['8.8.8.8','172.15.0.1','172.32.0.1','192.169.0.1','169.254.1.2','10.evil.com','192.168.1.2.evil.com','0.0.0.0'])assert.equal(isPrivateDevHost(h),false,h);
});
test('origin must match host and port; opaque and attacker origins blocked',()=>{
 assert.equal(allowedRequest('192.168.1.2:3000','http://192.168.1.2:3000'),true);
 for(const o of ['null','http://evil.com','http://192.168.1.2:4000','http://192.168.1.3:3000'])assert.equal(allowedRequest('192.168.1.2:3000',o),false,o);
 assert.equal(allowedRequest('8.8.8.8:3000'),false);
 assert.equal(allowedRequest('user:pass@192.168.1.2:3000'),false);
});
import {normalizePublicHost,forwardedProto} from './dev-lan-policy.mjs';
test('optional private HTTPS dev host: exact tailnet name only, off by default',()=>{
 const host='my-mac.tail1a2b3.ts.net';
 assert.equal(allowedRequest(host,`https://${host}`),false,'disabled unless configured');
 assert.equal(allowedRequest(host,`https://${host}`,{publicHost:host}),true);
 assert.equal(allowedRequest(host,undefined,{publicHost:host}),true);
 for(const bad of ['evil.tail1a2b3.ts.net','my-mac.tail1a2b3.ts.net.evil.com','evil.com','8.8.8.8'])assert.equal(allowedRequest(bad,undefined,{publicHost:host}),false,bad);
 assert.equal(allowedRequest(host,'https://evil.com',{publicHost:host}),false);
 assert.equal(allowedRequest(host,'null',{publicHost:host}),false);
});
test('configured host must be a *.ts.net DNS name, never an IP, wildcard or foreign domain',()=>{
 assert.equal(normalizePublicHost(' My-Mac.tail1a2b3.ts.net '),'my-mac.tail1a2b3.ts.net');
 for(const bad of ['','evil.com','*.ts.net','ts.net','http://a.ts.net','a.ts.net:443','1.2.3.4','a.b.ts.net.evil.com',undefined])assert.equal(normalizePublicHost(bad),null,String(bad));
});
test('forwarded protocol is https only for the configured host',()=>{
 const host='my-mac.tail1a2b3.ts.net';
 assert.equal(forwardedProto(host,{publicHost:host}),'https');
 assert.equal(forwardedProto('192.168.1.2:3000',{publicHost:host}),'http');
 assert.equal(forwardedProto(host,{}),'http');
});
