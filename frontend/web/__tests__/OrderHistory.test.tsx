import React from 'react';
import {render,screen,waitFor} from '@testing-library/react';
import {SWRConfig} from 'swr';
import {ViewOrdersModal} from '@/components/profile/ProfileModals';
import {api} from '@/lib/api';
jest.mock('@/lib/api',()=>({api:{get:jest.fn()}}));
jest.mock('framer-motion',()=>{
 const React=require('react');const tags=new Map();
 return {AnimatePresence:({children}:any)=>children,motion:new Proxy({}, {get:(_,tag)=>{
  if(!tags.has(tag))tags.set(tag,React.forwardRef(({children,initial,animate,exit,transition,layout,whileHover,whileTap,...props}:any,ref:any)=>React.createElement(tag,{...props,ref},children)));
  return tags.get(tag);
 }})};
});
it('uses authenticated API client, links old orders and displays stored currency/status',async()=>{
 jest.mocked(api.get).mockResolvedValue({data:{total:1,page:1,limit:10,orders:[{id:7,user_id:1,status:'in_transit',currency:'USD',total_price:25,created_at:'2026-11-22T10:00:00Z'}]}});
 render(<SWRConfig value={{provider:()=>new Map()}}><ViewOrdersModal isOpen onClose={()=>{}}/></SWRConfig>);
 expect(await screen.findByRole('link',{name:'View order 7'})).toHaveAttribute('href','/tracking/7');
 expect(screen.getByText(/USD\s*25\.00/)).toBeInTheDocument();
 expect(screen.getByText('In transit')).toBeInTheDocument();
 await waitFor(()=>expect(api.get).toHaveBeenCalledWith('/orders/me?page=1&limit=10'));
});
