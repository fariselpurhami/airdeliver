import { parseCartItems } from '@/lib/cart-snapshot';
const line={product_id:7,name:'Shoes',quantity:1,price:'10.00'};
it.each([null,undefined,true,'', '  ', 'Infinity',-1])('rejects unverified price %s',price=>{
 expect(()=>parseCartItems({items:[{...line,price}]})).toThrow();
});
it('preserves a genuinely listed zero',()=>expect(parseCartItems({items:[{...line,price:0}]})[0]?.price).toBe(0));
it('rejects duplicate lines and malformed quantities',()=>{
 expect(()=>parseCartItems({items:[line,line]})).toThrow();
 expect(()=>parseCartItems({items:[{...line,quantity:true}]})).toThrow();
 expect(()=>parseCartItems({items:[{...line,product_id:'7'}]})).toThrow();
});
