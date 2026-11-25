import React from 'react';
import {render,screen,fireEvent,within} from '@testing-library/react';
import Header from '@/components/layout/Header';
const mockPush=jest.fn();let mockStatus='authenticated';
jest.mock('next/navigation',()=>({usePathname:()=>'/products',useRouter:()=>({push:mockPush})}));
jest.mock('next-auth/react',()=>({useSession:()=>({status:mockStatus})}));
jest.mock('next/image',()=>function Image({priority,decoding,...p}:any){return <img {...p}/>});
beforeEach(()=>{mockPush.mockClear();mockStatus='authenticated';});
it('keeps icons hidden and inert until explicit tap, then toggles closed',()=>{
 render(<Header/>);
 const button=screen.getByRole('button',{name:'Toggle navigation'});
 const nav=screen.getByLabelText('Main navigation');
 expect(button).toHaveAttribute('aria-expanded','false');expect(nav).toHaveAttribute('inert');
 fireEvent.click(button);expect(button).toHaveAttribute('aria-expanded','true');expect(nav).not.toHaveAttribute('inert');
 expect(within(nav).getByRole('link',{name:'Home'})).toHaveAttribute('href','/');
 expect(within(nav).getByRole('link',{name:'Products'})).toHaveAttribute('aria-current','page');
 fireEvent.click(button);expect(button).toHaveAttribute('aria-expanded','false');
});
it('supports Escape and outside close without changing protected routing',()=>{
 mockStatus='unauthenticated';render(<Header/>);
 const button=screen.getByRole('button',{name:'Toggle navigation'});
 fireEvent.click(button);
 fireEvent.click(within(screen.getByLabelText('Main navigation')).getByRole('link',{name:'Profile'}));
 expect(mockPush).toHaveBeenCalledWith('/login?callbackUrl=%2Fprofile');
 fireEvent.click(button);fireEvent.keyDown(button,{key:'Escape'});expect(button).toHaveAttribute('aria-expanded','false');
 fireEvent.click(button);fireEvent.pointerDown(document.body);expect(button).toHaveAttribute('aria-expanded','false');
});
