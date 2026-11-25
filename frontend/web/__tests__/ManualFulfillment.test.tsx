import React from 'react';
import fs from 'fs';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {SWRConfig} from 'swr';
import {useSession} from 'next-auth/react';
import Page from '@/app/(admin)/dashboard/fulfillment/page';
import {api} from '@/lib/api';
jest.mock('next-auth/react',()=>({useSession:jest.fn()}));
jest.mock('@/lib/api',()=>({api:{get:jest.fn(),post:jest.fn()}}));
const order={id:7,status:'processing',is_paid:true,total_price:25,currency:'USD'};
function page(){return render(<SWRConfig value={{provider:()=>new Map()}}><Page/></SWRConfig>);}
beforeEach(()=>{jest.clearAllMocks();jest.mocked(useSession).mockReturnValue({data:{user:{role:'admin'}},status:'authenticated'} as any);jest.mocked(api.get).mockImplementation(async(url)=>({data:String(url).includes('/config')?{enabled:true}:{orders:[order],total_orders:1}}) as any);});
it('requires operator evidence and explicit review, never advances from page render',async()=>{
 page();await screen.findByText('Order #7');expect(api.post).not.toHaveBeenCalled();
 const review=screen.getByRole('button',{name:'Review: Assign to fulfillment'});expect(review).toBeDisabled();
 fireEvent.change(screen.getByRole('textbox'),{target:{value:'Assigned to warehouse operator fixture'}});fireEvent.click(review);
 expect(api.post).not.toHaveBeenCalled();
 if(process.env.FULFILLMENT_PREVIEW_HTML)fs.writeFileSync(process.env.FULFILLMENT_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/fulfillment-preview.css"></head><body style="margin:0">'+document.body.innerHTML+'</body></html>');
 jest.mocked(api.post).mockResolvedValue({data:{status:'assigned'}});
 fireEvent.click(screen.getByRole('button',{name:'Confirm operator attestation'}));
 await waitFor(()=>expect(api.post).toHaveBeenCalledWith('/admin/orders/7/fulfillment',{from_status:'processing',to_status:'assigned',evidence:'Assigned to warehouse operator fixture'}));
});
it('does not read orders for a nonadmin and explains access',()=>{
 jest.mocked(useSession).mockReturnValue({data:{user:{role:'user'}},status:'authenticated'} as any);page();
 expect(screen.getByRole('alert')).toHaveTextContent('administrator');expect(api.get).not.toHaveBeenCalled();
});
it('failure does not claim physical delivery or a successful update',async()=>{
 jest.mocked(api.post).mockRejectedValue(new Error('conflict'));page();await screen.findByText('Order #7');
 fireEvent.change(screen.getByRole('textbox'),{target:{value:'Assigned to warehouse operator fixture'}});
 fireEvent.click(screen.getByRole('button',{name:'Review: Assign to fulfillment'}));fireEvent.click(screen.getByRole('button',{name:'Confirm operator attestation'}));
 expect(await screen.findByRole('status')).toHaveTextContent('could not be confirmed');
});

it('default-off configuration exposes no order read or mutation controls',async()=>{
 jest.mocked(api.get).mockResolvedValue({data:{enabled:false}});page();
 expect(await screen.findByText(/Manual fulfillment is not enabled/)).toBeInTheDocument();expect(api.get).toHaveBeenCalledTimes(1);expect(api.post).not.toHaveBeenCalled();expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});
