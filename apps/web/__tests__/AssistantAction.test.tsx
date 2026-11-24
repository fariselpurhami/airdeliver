import React from 'react';
import fs from 'fs';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import AssistantAction from '@/components/ai/AssistantAction';
import {api} from '@/lib/api';
import {useCartStore} from '@/hooks/useCartStore';
jest.mock('@/lib/api',()=>({api:{post:jest.fn(),get:jest.fn()}}));
const action={action:'review_cart_change',payload:{review_id:'00000000-0000-4000-8000-000000000001',product_id:7,product_name:'Atlas headphones',operation:'add',quantity:2,price:'25.00',currency:'USD'}};
beforeEach(()=>{jest.clearAllMocks();useCartStore.setState({items:[]});Object.defineProperty(global.crypto,'randomUUID',{value:()=> '00000000-0000-4000-8000-000000000001',configurable:true});});
it('never mutates on model response and submits exact reviewed target only on explicit click',async()=>{
 jest.mocked(api.post).mockResolvedValue({});jest.mocked(api.get).mockResolvedValue({data:{items:[{product_id:7,name:'Atlas headphones',quantity:2,price:'25.00'}]}});
 render(<AssistantAction action={action}/>);
 expect(api.post).not.toHaveBeenCalled();
 if(process.env.ACTION_REVIEW_HTML)fs.writeFileSync(process.env.ACTION_REVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/actions-preview.css"></head><body style="margin:0;background:black;color:white;padding:20px;max-width:520px">'+document.body.innerHTML+'</body></html>');
 fireEvent.click(screen.getByRole('button',{name:'Confirm add to cart'}));
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('Request processed'));
 expect(api.post).toHaveBeenCalledWith('/ai-ordering/cart/add',{product_id:7,quantity:2},{headers:{'Idempotency-Key':'00000000-0000-4000-8000-000000000001'}});
 expect(useCartStore.getState().items[0]?.quantity).toBe(2);
 if(process.env.ACTION_PREVIEW_HTML)fs.writeFileSync(process.env.ACTION_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/actions-preview.css"></head><body style="margin:0;background:black;color:white;padding:20px;max-width:520px">'+document.body.innerHTML+'</body></html>');
});
it('keeps uncertain operation locked and offers authoritative cart review, not blind retry',async()=>{
 jest.mocked(api.post).mockRejectedValue(new Error('timeout'));render(<AssistantAction action={action}/>);
 fireEvent.click(screen.getByRole('button',{name:'Confirm add to cart'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Do not submit');
 expect(screen.queryByRole('button')).not.toBeInTheDocument();expect(api.post).toHaveBeenCalledTimes(1);
});
it('opens tracking only for a safe literal owned-order route',()=>{
 const {rerender}=render(<AssistantAction action={{action:'track_order',payload:{order_id:'7'}}}/>);
 expect(screen.getByRole('link')).toHaveAttribute('href','/tracking/7');
 rerender(<AssistantAction action={{action:'track_order',payload:{order_id:'../../admin'}}}/>);expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
it('does not pretend to create a human ticket or use model-supplied destination',()=>{
 render(<AssistantAction action={{action:'initiate_support_handoff',payload:{url:'https://untrusted.invalid'}}}/>);
 expect(screen.getByRole('status')).toHaveTextContent('No ticket or callback');expect(screen.getByRole('link')).toHaveAttribute('href','/help');
});
it('does not execute old model add_to_cart actions with user identifiers',()=>{
 render(<AssistantAction action={{action:'add_to_cart',payload:{userId:'other',sku:'7',qty:99}}}/>);expect(screen.queryByRole('button')).not.toBeInTheDocument();expect(api.post).not.toHaveBeenCalled();
});
it('requires explicit lifecycle click and explains save-list side effects',async()=>{
 jest.mocked(api.post).mockResolvedValue({data:{status:'saved'}});jest.mocked(api.get).mockResolvedValue({data:{items:[]}});
 render(<AssistantAction action={{action:'review_cart_lifecycle',payload:{review_id:action.payload.review_id,operation:'save',item_count:2}}}/>);
 expect(api.post).not.toHaveBeenCalled();expect(screen.getByText(/cancelled Saved List/)).toBeInTheDocument();
 if(process.env.LIFECYCLE_REVIEW_HTML)fs.writeFileSync(process.env.LIFECYCLE_REVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/actions-preview.css"></head><body style="margin:0;background:black;color:white;padding:20px;max-width:520px">'+document.body.innerHTML+'</body></html>');
 fireEvent.click(screen.getByRole('button',{name:'Confirm save list and clear cart'}));
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('Request confirmed'));
 expect(api.post).toHaveBeenCalledWith('/ai-ordering/cart/review/confirm',{review_id:action.payload.review_id});
});
it('locks uncertain lifecycle results with no retry button',async()=>{
 jest.mocked(api.post).mockRejectedValue(new Error('unconfirmed'));
 render(<AssistantAction action={{action:'review_cart_lifecycle',payload:{review_id:action.payload.review_id,operation:'clear',item_count:2}}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Confirm clear active cart'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Do not retry blindly');expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
