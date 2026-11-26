import {beforeAll} from '@jest/globals';
import React from 'react';
import {render,screen,fireEvent} from '@testing-library/react';
import Chatbot from '@/components/ai/Chatbot';
let mockIsOpen=true;
const sendMessage=jest.fn(),setIsOpen=jest.fn();
jest.mock('@/hooks/useAISupportStore',()=>({useAISupportStore:()=>({isOpen:mockIsOpen,setIsOpen,sendMessage,isLoading:false,messages:[{id:'a',sender:'ai',data:{text:'How can I help?',action:null,explain:'Initial greeting.'}}]})}));
jest.mock('@/hooks/useAIOrderingStore',()=>({useAIOrderingStore:(selector:any)=>selector({isOverlayVisible:false})}));
jest.mock('@/hooks/useUIStore',()=>({useUIStore:(selector:any)=>selector({isProductOverlayVisible:false})}));
jest.mock('@/hooks/useBodyScrollLock',()=>({useBodyScrollLock:jest.fn()}));
beforeAll(()=>{Element.prototype.scrollIntoView=jest.fn();});
it('keeps assistant identity, responsive dialog and existing send/close wiring',()=>{
 render(<Chatbot/>);
 expect(screen.getByRole('dialog',{name:'Air Assistant'})).toHaveClass('max-w-[520px]');
 const input=screen.getByRole('textbox',{name:'Message Air Assistant'});
 fireEvent.change(input,{target:{value:'Where is my order?'}});
 fireEvent.keyDown(input,{key:'Enter'});
 expect(sendMessage).toHaveBeenCalledWith('Where is my order?');
 fireEvent.click(screen.getByLabelText('Close assistant panel'));
 expect(setIsOpen).toHaveBeenCalledWith(false);
 expect(screen.getByText('How can I help?')).toBeVisible();
});

it('keeps the unframed launcher accessible and opens the same assistant',()=>{
 mockIsOpen=false;
 render(<Chatbot/>);
 const button=screen.getByRole('button',{name:'Open Air Assistant'});
 expect(button).toHaveClass('focus-visible:ring-2');
 expect(button).toHaveClass('bg-transparent','border-0','shadow-none');
 // The launcher button itself stays unframed; the user asked (phonemsg-01M8BGPHPN6GCKRZSVN787YE7E,
 // 01M8BGSM...) for a barely visible glass disc behind the robot, so the disc is the one framed element.
 const glass=button.querySelector('[data-testid="chatbot-launcher-glass"]');
 expect(glass).toHaveClass('text-cyan-100','rounded-full','backdrop-blur-md','w-11','h-11');
 expect(glass).not.toHaveClass('bg-white');
 expect(button).not.toHaveClass('rounded-full','backdrop-blur-xl');
 fireEvent.click(button);expect(setIsOpen).toHaveBeenCalledWith(true);
 mockIsOpen=true;
});
