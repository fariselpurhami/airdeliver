import React from 'react';
import fs from 'fs';
import {render,screen,waitFor,fireEvent} from '@testing-library/react';
import {SWRConfig} from 'swr';
import TrackingPage from '@/app/(main)/tracking/[orderId]/page';
import {api} from '@/lib/api';
import {orderMoney,orderStatus} from '@/lib/order-display';
let routeId='7';
jest.mock('next/navigation',()=>({useParams:()=>({orderId:routeId})}));
jest.mock('@/lib/api',()=>({api:{get:jest.fn()}}));
const fixture={id:7,status:'processing',currency:'CAD',total_price:25,created_at:'2026-11-22T10:00:00Z',updated_at:'2026-11-23T10:00:00Z',items:[{id:1,product_id:8,quantity:2,price_per_unit:12.5,product:{name:'Fixture headphones'}}]};
function page(){return render(<SWRConfig value={{provider:()=>new Map(),dedupingInterval:0}}><TrackingPage/></SWRConfig>);}
beforeEach(()=>{jest.clearAllMocks();routeId='7';jest.mocked(api.get).mockResolvedValue({data:fixture});});
it('fetches owned order directly, shows real currency and states carrier limitations',async()=>{
 page();
 expect(await screen.findByText('Fixture headphones × 2')).toBeInTheDocument();
 expect(api.get).toHaveBeenCalledWith('/orders/me/7');
 expect(screen.getAllByText(/CAD\s*25\.00/)).toHaveLength(2);
 expect(screen.getByText(/not live carrier tracking/)).toBeInTheDocument();
 expect(screen.getByText(/Payment confirmed, processing/)).toBeInTheDocument();
 expect(screen.getByText(/Order record last updated/)).toBeInTheDocument();
 if(process.env.TRACKING_PREVIEW_HTML)fs.writeFileSync(process.env.TRACKING_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/tracking-preview.css"></head><body style="margin:0">'+document.body.innerHTML+'</body></html>');
});
it('treats404 as account-scoped absence, not global nonexistence',async()=>{
 jest.mocked(api.get).mockRejectedValue({response:{status:404},message:'raw-private-error'});page();
 expect(await screen.findByRole('alert')).toHaveTextContent('Order not found in your account');
 expect(screen.queryByText('raw-private-error')).not.toBeInTheDocument();
});
it('offers sign in for expired session without claiming missing order',async()=>{
 jest.mocked(api.get).mockRejectedValue({response:{status:401}});page();
 expect(await screen.findByRole('link',{name:'Sign in'})).toHaveAttribute('href','/login?callbackUrl=%2Ftracking%2F7');
});
it('preserves last view but warns on refresh failure and allows recovery',async()=>{
 page();await screen.findByText('Fixture headphones × 2');
 jest.mocked(api.get).mockRejectedValueOnce({response:{status:503}});
 fireEvent.click(screen.getByRole('button',{name:'Refresh status'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('last saved view');
 expect(screen.getByText('Fixture headphones × 2')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Refresh status'}));
 await waitFor(()=>expect(screen.queryByRole('alert')).not.toBeInTheDocument());
});
it.each(['0','-1','junk','2147483648','7/other'])('does not request invalid order%s',async value=>{
 routeId=value;page();expect(screen.getByRole('alert')).toHaveTextContent('invalid');expect(api.get).not.toHaveBeenCalled();
});
it('never guesses currency or shows NaN and does not invent unknown status',()=>{
 expect(orderMoney(5,undefined)).toBe('Amount unavailable');
 expect(orderMoney(NaN,'USD')).toBe('Amount unavailable');
 expect(orderMoney(-1,'USD')).toBe('Amount unavailable');
 expect(orderStatus('surprise').label).toBe('Status unavailable');
 expect(orderStatus('saved_for_later').label).toContain('not purchased');
});
