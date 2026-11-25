import fs from 'fs';
import path from 'path';
const read=(p:string)=>fs.readFileSync(path.join(process.cwd(),p),'utf8');
it('keeps the continuous home surface free of a repeated dot pattern',()=>{
 const css=read('src/app/globals.css').split('.home-continuous-background {')[1]!.split('}')[0];
 expect(css).not.toContain('radial-gradient(circle at 1px');
 expect(css).not.toContain('background-size: 24px');
});
it('keeps lower landing sections free of grid overlays and decorative heading font',()=>{
 const source=read('src/app/(main)/_components/LandingClient.tsx');
 const lower=source.slice(source.indexOf('interface StepItem'),source.indexOf('const TrustedBySection'));
 expect(lower).not.toContain('linear-gradient(to right');
 expect(lower).not.toContain('Orbitron');
 expect(lower).toContain('HowItWorksSection');expect(lower).toContain('SIGN UP');
});
