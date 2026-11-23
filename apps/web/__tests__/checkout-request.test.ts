import { beforeAll, afterAll } from '@jest/globals';
import { webcrypto } from 'node:crypto';
import { TextEncoder } from 'node:util';
import { getCheckoutRequestKey, retireCheckoutRequestKey } from '@/lib/checkout-request';

const realCrypto=globalThis.crypto;
beforeAll(()=>{
  Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
  Object.defineProperty(globalThis,'TextEncoder',{value:TextEncoder,configurable:true});
});
afterAll(()=>{Object.defineProperty(globalThis,'crypto',{value:realCrypto,configurable:true});});
beforeEach(()=>localStorage.clear());
const token=(sub:string)=>`${btoa('{}')}.${btoa(JSON.stringify({sub}))}.test`;
const cart=[{id:7,price:'10.50',quantity:2}];
it('persists and reuses the exact request key across retries',async()=>{
  const first=await getCheckoutRequestKey(token('buyer'),{b:2,a:1},cart);
  const next=await getCheckoutRequestKey(token('buyer'),{a:1,b:2},cart);
  expect(next).toBe(first);
  expect(localStorage.length).toBe(1);
  expect(localStorage.key(0)).not.toContain('buyer');
});
it('isolates account, delivery details and cart intent',async()=>{
  const base=await getCheckoutRequestKey(token('buyer'),{line1:'123 Street'},cart);
  expect(await getCheckoutRequestKey(token('another'),{line1:'123 Street'},cart)).not.toBe(base);
  expect(await getCheckoutRequestKey(token('buyer'),{line1:'456 Street'},cart)).not.toBe(base);
  expect(await getCheckoutRequestKey(token('buyer'),{line1:'123 Street'},[{...cart[0]!,quantity:3}])).not.toBe(base);
});
it('does not silently lose retry identity when browser persistence fails',async()=>{
  const storage={getItem:()=>null,setItem:()=>{throw new Error('quota');},removeItem:()=>{}};
  await expect(getCheckoutRequestKey(token('buyer'),{},cart,storage)).rejects.toThrow('quota');
});
it('retires only a server-confirmed paid checkout key',async()=>{
  const paid=await getCheckoutRequestKey(token('buyer'),{},cart);
  const other=await getCheckoutRequestKey(token('another'),{},cart);
  retireCheckoutRequestKey(paid);
  expect(await getCheckoutRequestKey(token('another'),{},cart)).toBe(other);
  expect(await getCheckoutRequestKey(token('buyer'),{},cart)).not.toBe(paid);
});
it('fails closed with a useful message when secure digest is unavailable on HTTP LAN',async()=>{
 Object.defineProperty(globalThis,'crypto',{value:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},configurable:true});
 await expect(getCheckoutRequestKey(token('buyer'),{},cart)).rejects.toThrow('Checkout needs a secure browser connection');
 expect(localStorage.length).toBe(0);
 Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
});
