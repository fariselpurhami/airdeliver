import React from 'react';
import fs from 'fs';
import { render,screen,cleanup } from '@testing-library/react';
import AppShell from '@/components/layout/AppShell';
import AIChatOverlay from '@/components/ai/AIChatOverlay';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
jest.mock('next-auth/react',()=>({useSession:()=>({status:'unauthenticated',data:null})}));
jest.mock('next/navigation',()=>({useRouter:()=>({push:jest.fn()}),usePathname:()=>'/'}));
jest.mock('next/dynamic',()=>()=>function Deferred(){return null});
jest.mock('next/image',()=>({__esModule:true,default:({src,alt,...props}:any)=><img src={typeof src==='string'?src:src.src} alt={alt}/>}));
jest.mock('react-markdown',()=>({__esModule:true,default:({children}:any)=><p>{children}</p>}));
jest.mock('remark-gfm',()=>({__esModule:true,default:()=>null}));
beforeEach(()=>{window.scrollTo=jest.fn();});
afterEach(()=>{cleanup();useAIOrderingStore.setState({isOverlayVisible:false,messages:[]});});
it('one shell-owned live overlay, hidden inert chrome, readable mobile surface',()=>{
 useAIOrderingStore.setState({isOverlayVisible:true,messages:[]});
 const view=render(<AppShell><AIChatOverlay isOpen onClose={jest.fn()}/><p>Underlying home</p></AppShell>);
 expect(screen.getAllByRole('button',{name:'Close overlay'})).toHaveLength(1);
 const main=view.container.querySelector('main')!;
 expect(main).toHaveAttribute('inert');expect(main).toHaveAttribute('aria-hidden','true');
 expect(view.container.querySelector('header')!.parentElement).toHaveAttribute('hidden');
 expect(view.container.querySelector('.app-shell')).toHaveAttribute('data-ordering-open','true');
 if(process.env.HOME_LAYER_PREVIEW)fs.writeFileSync('/tmp/home-overlay-after.html','<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/home-layer.css"></head><body style="margin:0;background:#04060a;color:white">'+view.container.innerHTML+'</body></html>');
});
it('keeps site chrome and content available after closing',()=>{
 useAIOrderingStore.setState({isOverlayVisible:false});
 const view=render(<AppShell><p>Underlying home</p></AppShell>);
 expect(view.container.querySelector('main')).not.toHaveAttribute('inert');
 expect(screen.queryByRole('button',{name:'Close overlay'})).not.toBeInTheDocument();
 expect(view.container.querySelector('header')!.parentElement).not.toHaveAttribute('hidden');
});
it('does not tile full-page color gradients and pauses hidden canvas work',()=>{
 const css=fs.readFileSync('app/globals.css','utf8');
 expect(css).toContain('background-repeat: no-repeat,no-repeat,repeat');
 const home=fs.readFileSync('app/(main)/_components/LandingClient.tsx','utf8');
 expect(home).toContain('if (orderingOpen) return;');
 expect(home).toContain('[prefersReducedMotion, orderingOpen]');
});
