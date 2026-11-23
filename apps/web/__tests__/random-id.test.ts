import {randomId} from '@/lib/random-id';
import {webcrypto} from 'node:crypto';
import fs from 'fs';
const original=globalThis.crypto;
afterEach(()=>{Object.defineProperty(globalThis,'crypto',{value:original,configurable:true});});
it('uses native cryptographic UUID when available',()=>{
 const native=jest.fn(()=> 'native-uuid');Object.defineProperty(globalThis,'crypto',{value:{randomUUID:native},configurable:true});expect(randomId()).toBe('native-uuid');expect(native).toHaveBeenCalledTimes(1);
});
it('generates correct v4 version and variant from cryptographic bytes without randomUUID',()=>{
 const bytes=jest.fn((target:Uint8Array)=>{target.fill(255);return target;});Object.defineProperty(globalThis,'crypto',{value:{getRandomValues:bytes},configurable:true});
 expect(randomId()).toBe('ffffffff-ffff-4fff-bfff-ffffffffffff');expect(bytes).toHaveBeenCalledTimes(1);expect(bytes.mock.calls[0]![0]).toHaveLength(16);
});
it('real getRandomValues fallback produces distinct valid UUIDs without Math.random',()=>{
 Object.defineProperty(globalThis,'crypto',{value:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},configurable:true});
 const ids=Array.from({length:1000},()=>randomId());expect(new Set(ids).size).toBe(1000);for(const id of ids)expect(id).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/);
});
it('fails closed when no cryptographic entropy exists',()=>{
 Object.defineProperty(globalThis,'crypto',{value:undefined,configurable:true});expect(()=>randomId()).toThrow('Secure random');
});
it('all application UUID call sites use the shared helper',()=>{
 for(const file of ['app/(main)/_components/LandingClient.tsx','app/(main)/page.tsx','app/layout.tsx','lib/checkout-request.ts','hooks/useAIOrderingStore.ts']){
  const source=fs.readFileSync(file,'utf8');expect(source).not.toContain('crypto.randomUUID');expect(source).toContain('randomId');
 }
});
