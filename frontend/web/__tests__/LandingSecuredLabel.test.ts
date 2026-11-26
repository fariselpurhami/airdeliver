import fs from 'fs';
it('landing taglines say Secured, not 100% Autonomous',()=>{
 for(const file of ['src/app/(main)/_components/LandingClient.tsx','src/components/home/MobileLandingView.tsx']){
  const source=fs.readFileSync(file,'utf8');
  expect(source).not.toMatch(/100% ?Autonomous/i);
  expect(source).toMatch(/Secured/);
 }
});
