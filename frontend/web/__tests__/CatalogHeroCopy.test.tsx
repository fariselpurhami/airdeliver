import React from 'react';
import fs from 'fs';
import {render,screen} from '@testing-library/react';
import ProductsPage from '@/app/(main)/products/page';
jest.mock('next-auth/react',()=>({useSession:()=>({status:'unauthenticated',data:null})}));
jest.mock('next/navigation',()=>({useRouter:()=>({push:jest.fn()}),usePathname:()=>'/products'}));
jest.mock('swr',()=>({__esModule:true,default:()=>({data:[],isLoading:false,error:null})}));
jest.mock('@react-three/fiber',()=>({Canvas:()=>null,useFrame:()=>{}}));
jest.mock('@react-three/drei',()=>({Points:()=>null,PointMaterial:()=>null}));
jest.mock('next/dynamic',()=>()=>()=>null);
jest.mock('@/components/hero/FloatingHeroCards',()=>({FloatingHeroCards:()=>null,HERO_STAGE_CLASSES:'relative min-h-screen flex items-center justify-center'}));
jest.mock('@/components/hero/MobileHomeFloatingCards',()=>({MobileHomeFloatingCards:()=>null}));
jest.mock('@/components/ai/AIChatOverlay',()=>()=>null);
it('renders only the retained catalog hero sentence',()=>{
 const view=render(<ProductsPage/>);
 expect(screen.getByText("Don't search. Just ask.")).toBeInTheDocument();
 expect(screen.queryByText(/scans thousands|instant air-drop/)).not.toBeInTheDocument();
 if(process.env.CATALOG_HERO_PREVIEW)fs.writeFileSync('/tmp/catalog-hero-copy-render.html','<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/home-layer.css"></head><body style="margin:0;background:#04060a;color:white">'+view.container.innerHTML+'</body></html>');
});
