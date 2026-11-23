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
