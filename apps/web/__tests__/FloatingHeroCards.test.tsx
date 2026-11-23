import React from 'react';
import { render } from '@testing-library/react';
import fs from 'fs';
import { FloatingHeroCards, HERO_STAGE_CLASSES } from '@/components/hero/FloatingHeroCards';
jest.mock('next/image',()=>({__esModule:true,default:({fill,...props}:any)=><img {...props}/>}));
it('renders one shared six-card layout with a protected center',()=>{
 const {container}=render(<FloatingHeroCards/>);
 expect(container.querySelectorAll('[data-hero-card]')).toHaveLength(6);
 expect(HERO_STAGE_CLASSES).toContain('min-h-[1000px]');
 for(const file of ['app/(main)/products/page.tsx','app/(main)/_components/LandingClient.tsx']){
  const source=fs.readFileSync(file,'utf8');
  expect(source).toContain('<FloatingHeroCards />');
  expect(source).toContain('HERO_STAGE_CLASSES');
 }
});

it('preserves the original eight-card mobile home distribution',()=>{
 const source=fs.readFileSync('app/(main)/_components/LandingClient.tsx','utf8');
 expect(source).toContain('MobileHomeHeroSection');
 expect(source).toContain('isMobile ? <MobileHomeHeroSection');
 expect(source).toContain('HERO_CARDS.map');
});
