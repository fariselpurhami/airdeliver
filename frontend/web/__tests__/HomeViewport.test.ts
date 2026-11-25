import fs from 'fs';
it('covers the viewport and keeps atmosphere through section spacing',()=>{
 const css=fs.readFileSync('app/globals.css','utf8');
 expect(css).toContain('.home-viewport-hero');expect(css).toContain('100dvh');
 expect(css).toContain('.home-continuous-background');
 const home=fs.readFileSync('app/(main)/_components/LandingClient.tsx','utf8');expect(home).toContain('home-viewport-hero');expect(home).toContain('home-continuous-background');
 const mobile=fs.readFileSync('components/home/MobileLandingView.tsx','utf8');expect(mobile).toContain('min-h-[100dvh]');
});
