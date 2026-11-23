import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import { useCartStore } from '@/hooks/useCartStore';
const original=useAIOrderingStore.getState();
beforeEach(()=>{useAIOrderingStore.setState({messages:[],cartRevision:null});useCartStore.setState({items:[]});});
afterEach(()=>useAIOrderingStore.setState(original,true));
const preview=(revision?:unknown,id=1)=>useAIOrderingStore.getState().addSocketAIMessage({type:'cart_preview',content:{items:[{product_id:id,name:'Shoes',price:'10',quantity:1}],...(revision===undefined?{}:{revision})}});
it('ignores delayed and repeated revisions after accepting a newer cart',()=>{
 preview(2,2);preview(1,1);preview(2,3);
 expect(useCartStore.getState().items[0]?.id).toBe(2);
 expect(useAIOrderingStore.getState().messages).toHaveLength(1);
 preview(3,3);expect(useCartStore.getState().items[0]?.id).toBe(3);
});
it('preserves legacy flow until revisioned state is seen, then blocks unordered rewind',()=>{
 preview(undefined,1);expect(useCartStore.getState().items[0]?.id).toBe(1);
 preview(0,2);preview(undefined,3);expect(useCartStore.getState().items[0]?.id).toBe(2);
});
it.each([-1,1.5,'2',null,Number.MAX_SAFE_INTEGER+1])('rejects malformed revision %s',revision=>{
 preview(revision);expect(useCartStore.getState().items).toEqual([]);
});
