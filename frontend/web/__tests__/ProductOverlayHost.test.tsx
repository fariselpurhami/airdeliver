import React from 'react';
import fs from 'fs';
import { render,screen,fireEvent,cleanup,act } from '@testing-library/react';
import ProductOverlay from '@/components/products/ProductOverlay';
import AppShell from '@/components/layout/AppShell';
import {useUIStore} from '@/hooks/useUIStore';
import {useAIOrderingStore} from '@/hooks/useAIOrderingStore';
jest.mock('swr',()=>({__esModule:true,default:()=>({data:[{id:1,name:'Local test shirt',price:24,inventory:4,image:null,description:'Synthetic local test product',category:'Fashion'}],isLoading:false})}));
jest.mock('next-auth/react',()=>({useSession:()=>({status:'unauthenticated',data:null})}));
jest.mock('next/navigation',()=>({useRouter:()=>({push:jest.fn()}),usePathname:()=>'/'}));
jest.mock('next/dynamic',()=>()=>function Deferred(){return null});
jest.mock('next/image',()=>({__esModule:true,default:({src,alt}:any)=><img src={typeof src==='string'?src:src.src} alt={alt}/>}));
jest.mock('react-markdown',()=>({__esModule:true,default:()=>null}));
jest.mock('remark-gfm',()=>({__esModule:true,default:()=>null}));
beforeEach(()=>{window.scrollTo=jest.fn();useAIOrderingStore.setState({isOverlayVisible:false});});
afterEach(()=>{cleanup();useUIStore.setState({isProductOverlayVisible:false});});
it('portals products outside inert home, hides site chrome and restores on close',()=>{
 function Harness(){const open=useUIStore(s=>s.isProductOverlayVisible);return <AppShell><button onClick={()=>useUIStore.getState().showProductOverlay()}>Explore</button><div style={{transform:'translateZ(0)',isolation:'isolate'}}><ProductOverlay isOpen={open} onClose={()=>useUIStore.getState().hideProductOverlay()}/></div></AppShell>}
 const view=render(<Harness/>);
 fireEvent.click(screen.getByRole('button',{name:'Explore'}));
 const dialog=screen.getByRole('dialog',{name:'Trending products'});
 expect(dialog.closest('main')).toBeNull();expect(dialog.closest('[inert]')).toBeNull();
 expect(view.container.querySelector('header')!.parentElement).toHaveAttribute('hidden');
 expect(screen.getByRole('button',{name:'Close products'})).toBeVisible();
 if(process.env.PRODUCT_OVERLAY_PREVIEW){
  dialog.parentElement!.style.opacity='1';(dialog as HTMLElement).style.opacity='1';(dialog as HTMLElement).style.transform='none';
  fs.writeFileSync('/tmp/trending-overlay-render.html','<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><link rel="stylesheet" href="file:///tmp/trending-overlay.css"></head><body style="margin:0;background:#04060a;color:white">'+document.body.innerHTML+'</body></html>');
 }
 fireEvent.click(screen.getByRole('button',{name:'Close products'}));
 expect(view.container.querySelector('header')!.parentElement).not.toHaveAttribute('hidden');
 expect(view.container.querySelector('main')).not.toHaveAttribute('inert');
});
