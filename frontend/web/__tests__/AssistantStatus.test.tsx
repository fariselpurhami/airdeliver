import React from 'react';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import AssistantStatus from '@/components/ai/AssistantStatus';
const send=jest.fn(),opening=jest.fn();
let messages:any[]=[];let loading=false;
jest.mock('@/hooks/useAIOrderingStore',()=>({useAIOrderingStore:(selector:any)=>selector({messages,isLoading:loading,sendMessage:send,fetchInitialSuggestions:opening})}));
beforeEach(()=>{send.mockClear();opening.mockClear();loading=false;messages=[{id:1,sender:'user',contentType:'text',content:'Which laptop matches my budget?'},{id:2,sender:'ai',contentType:'info'}];});
const text="I can't answer your shopping question right now. Please try again later, or browse products.";
it('makes no call on render; retries only the original user question on a click',()=>{
 render(<AssistantStatus code="capacity" recovery="retry_chat" text={text} messageId={2}/>);
 expect(send).not.toHaveBeenCalled();expect(opening).not.toHaveBeenCalled();
 expect(screen.getByRole('status')).toHaveTextContent(text);
 expect(screen.getByRole('link',{name:'Browse products'})).toHaveAttribute('href','/products');
 fireEvent.click(screen.getByRole('button',{name:'Try question again'}));
 expect(send).toHaveBeenCalledTimes(1);expect(send).toHaveBeenCalledWith(messages[0].content);
 expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
it('opening retry is explicit and never submits a shopping message',()=>{
 render(<AssistantStatus code="opening_unverified" recovery="retry_opening" text={text} messageId={2}/>);
 fireEvent.click(screen.getByRole('button',{name:'Reload selection'}));
 expect(opening).toHaveBeenCalledTimes(1);expect(send).not.toHaveBeenCalled();
});
it('old statuses, queued commands, images and unknown codes cannot replay',()=>{
 for(const change of [()=>{messages.push({id:3,sender:'user',contentType:'text',content:'new question'});},()=>{messages[0].contentType='image_user_upload';},()=>{messages=[];},()=>{loading=true;}]){
 messages=[{id:1,sender:'user',contentType:'text',content:'Question'},{id:2,sender:'ai',contentType:'info'}];loading=false;change();
 const view=render(<AssistantStatus code="capacity" recovery="retry_chat" text={text} messageId={2}/>);expect(screen.queryByRole('button')).not.toBeInTheDocument();view.unmount();
 }
 const view=render(<AssistantStatus code="checkout_payment_retry" recovery="retry_chat" text={text} messageId={2}/>);expect(view.container).toHaveTextContent(text);expect(screen.queryByRole('button')).not.toBeInTheDocument();
 expect(send).not.toHaveBeenCalled();expect(opening).not.toHaveBeenCalled();
});
it('renders visual evidence',()=>{
 const view=render(<main className="mx-auto max-w-md space-y-6 p-6 pt-12 text-white"><h1 className="text-2xl font-medium">Order with Air</h1><AssistantStatus code="opening_unverified" recovery="retry_opening" text="I couldn't finish the introduction for this selection. You can try loading it again or explore the catalog directly." messageId={2}/><p className="rounded-2xl bg-white/10 p-4 text-sm">Which laptop is available right now?</p><AssistantStatus code="capacity" recovery="retry_chat" text={text} messageId={2}/></main>);
 if(process.env.STATUS_PREVIEW_HTML)require('fs').writeFileSync(process.env.STATUS_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="file:///tmp/human-status.css"></head><body style="margin:0;background:#05070c;font-family:Arial,sans-serif">'+view.container.innerHTML+'</body></html>');
});
