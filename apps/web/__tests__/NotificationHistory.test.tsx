import React from 'react';
import fs from 'fs';
import {render,screen,fireEvent,waitFor,act} from '@testing-library/react';
import {SWRConfig} from 'swr';
import Page from '@/app/(main)/notifications/page';
import {api} from '@/lib/api';
jest.mock('@/lib/api',()=>({api:{get:jest.fn(),post:jest.fn(),delete:jest.fn()}}));
jest.mock('@react-three/fiber',()=>({Canvas:()=>null,useFrame:jest.fn()}));
jest.mock('@react-three/drei',()=>({Stars:()=>null}));
jest.mock('framer-motion',()=>{const React=require('react');const tags=new Map();return {AnimatePresence:({children}:any)=>children,motion:new Proxy({},{get:(_,tag)=>{if(!tags.has(tag))tags.set(tag,React.forwardRef(({children,initial,animate,exit,transition,layout,whileHover,whileTap,...props}:any,ref:any)=>React.createElement(tag,{...props,ref},children)));return tags.get(tag);}})};});
const fixture={id:1,title:'Order marked in transit',body:'An operator updated the order, not a carrier scan.',type:'order_update',read:false,cta:'/tracking/7',timestamp:'1 min ago',created_at:'2026-11-23T12:00:00Z'};
beforeEach(()=>{jest.clearAllMocks();jest.mocked(api.get).mockResolvedValue({data:{items:[fixture],total:25}});});
function page(){return render(<SWRConfig value={{provider:()=>new Map(),dedupingInterval:0}}><Page/></SWRConfig>);}
it('opens safe order link, paginates and states delivery-channel limits',async()=>{
 page();expect(await screen.findByRole('link',{name:'Open order'})).toHaveAttribute('href','/tracking/7');
 expect(screen.getByText(/not proof an email or push/)).toBeInTheDocument();
 if(process.env.NOTIFICATION_PREVIEW_HTML)fs.writeFileSync(process.env.NOTIFICATION_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/notification-preview.css"></head><body style="margin:0">'+document.body.innerHTML+'</body></html>');
 fireEvent.click(screen.getByRole('button',{name:'Next'}));await waitFor(()=>expect(api.get).toHaveBeenCalledWith('/notifications/history?page=2&limit=20'));
});
it('does not open arbitrary notification destinations',async()=>{
 jest.mocked(api.get).mockResolvedValue({data:{items:[{...fixture,cta:'https://untrusted.invalid'}],total:1}});page();await screen.findByText(fixture.title);expect(screen.queryByRole('link',{name:'Open order'})).not.toBeInTheDocument();
});
it('read failure remains visible instead of silently claiming saved',async()=>{
 jest.mocked(api.post).mockRejectedValue(new Error('offline'));page();await screen.findByText(fixture.title);fireEvent.click(screen.getByTitle('Mark Read'));expect(await screen.findByRole('alert')).toHaveTextContent('could not be saved');
});

it('dismiss failure is visible and recovers saved notices without an unhandled rejection',async()=>{
 jest.mocked(api.delete).mockRejectedValue(new Error('uncertain'));page();await screen.findByText(fixture.title);
 jest.useFakeTimers();fireEvent.click(screen.getByTitle('Dismiss'));expect(screen.queryByText(fixture.title)).not.toBeInTheDocument();
 await act(async()=>{jest.advanceTimersByTime(4100);await Promise.resolve();});jest.useRealTimers();
 expect(await screen.findByRole('alert')).toHaveTextContent('Dismissal could not be confirmed');expect(await screen.findByText(fixture.title)).toBeInTheDocument();
});
it('undo prevents the delete and restores the saved notice',async()=>{
 page();await screen.findByText(fixture.title);jest.useFakeTimers();fireEvent.click(screen.getByTitle('Dismiss'));
 fireEvent.click(screen.getByRole('button',{name:'Undo'}));await act(async()=>{jest.advanceTimersByTime(4100);});jest.useRealTimers();
 expect(api.delete).not.toHaveBeenCalled();expect(screen.getByText(fixture.title)).toBeInTheDocument();
});
