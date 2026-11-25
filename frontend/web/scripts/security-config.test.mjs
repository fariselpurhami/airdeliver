import assert from 'node:assert/strict';
import test from 'node:test';
import config from '../next.config.mjs';
import remote from 'next/dist/shared/lib/match-remote-pattern.js';

test('production builds reject TypeScript errors and do not log full fetch URLs',()=>{
 assert.notEqual(config.typescript?.ignoreBuildErrors,true);
 assert.notEqual(config.logging?.fetches?.fullUrl,true);
});

test('image optimizer rejects arbitrary hosts, plaintext remote URLs and SVG optimization',()=>{
 assert.notEqual(config.images.dangerouslyAllowSVG,true);
 for(const url of ['http://evil.test/a.png','https://evil.test/a.png','http://169.254.169.254/latest/meta-data','https://localhost/a.png']) {
  assert.equal(remote.hasRemoteMatch([],config.images.remotePatterns,new URL(url)),false,url);
 }
 assert.equal(remote.hasRemoteMatch([],config.images.remotePatterns,new URL('https://images.unsplash.com/photo-test')),true);
 assert.equal(remote.hasRemoteMatch([],config.images.remotePatterns,new URL('https://ui-avatars.com/api/?name=Demo')),true);
});
