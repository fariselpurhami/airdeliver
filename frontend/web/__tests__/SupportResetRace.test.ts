import {useAIOrderingStore} from '@/hooks/useAIOrderingStore';

describe('support HTTP response lifetime follows the visible conversation',()=>{
 let snapshot:ReturnType<typeof useAIOrderingStore.getState>;
 let fetchBefore:typeof fetch;
 beforeEach(()=>{
  snapshot=useAIOrderingStore.getState();fetchBefore=global.fetch;
  useAIOrderingStore.setState({messages:[],ackTimeouts:{},clearCart:jest.fn(),_sendInternalCommand:jest.fn(),fetchInitialSuggestions:jest.fn()});
 });
 afterEach(()=>{useAIOrderingStore.setState(snapshot,true);global.fetch=fetchBefore;});
 it.each(['success','error'])('does not publish delayed pre-reset %s into a new conversation',async mode=>{
  let complete!:(value:Response)=>void;
  global.fetch=jest.fn<typeof fetch>().mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
  const pending=useAIOrderingStore.getState()._postSupportChat('old private question',null);
  useAIOrderingStore.getState().resetChat();
  const resetMessages=useAIOrderingStore.getState().messages;
  complete({ok:mode==='success',json:async()=>({text:'old private answer',products:[],response_kind:'conversation'})} as Response);
  await pending;
  expect(useAIOrderingStore.getState().messages).toEqual(resetMessages);
 });
 it('still publishes an ordinary reply in the unchanged conversation',async()=>{
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({text:'current answer',products:[],response_kind:'conversation'})} as Response);
  await useAIOrderingStore.getState()._postSupportChat('current question',null);
  expect(useAIOrderingStore.getState().messages.some(message=>message.content==='current answer')).toBe(true);
 });
});

it('suppresses a reply whose response body resolves after reset, without blocking a new reply',async()=>{
 const snapshot=useAIOrderingStore.getState();const before=global.fetch;
 let body!:(value:unknown)=>void;
 const oldBody=new Promise(resolve=>{body=resolve;});
 global.fetch=jest.fn<typeof fetch>()
  .mockResolvedValueOnce({ok:true,json:()=>oldBody} as Response)
  .mockResolvedValueOnce({ok:true,json:async()=>({text:'new current answer',products:[]})} as Response);
 try{
  useAIOrderingStore.setState({messages:[],ackTimeouts:{},clearCart:jest.fn(),_sendInternalCommand:jest.fn(),fetchInitialSuggestions:jest.fn()});
  const old=useAIOrderingStore.getState()._postSupportChat('old',null);
  await Promise.resolve();
  useAIOrderingStore.getState().resetChat();
  await useAIOrderingStore.getState()._postSupportChat('new',null);
  body({text:'stale body',products:[]});await old;
  const messages=useAIOrderingStore.getState().messages;
  expect(messages.some(m=>m.content==='new current answer')).toBe(true);
  expect(messages.some(m=>m.content==='stale body')).toBe(false);
 }finally{useAIOrderingStore.setState(snapshot,true);global.fetch=before;}
});

it('does not restore an old failure after two resets and a new pending question',async()=>{
 const snapshot=useAIOrderingStore.getState();const before=global.fetch;
 let reject!:(reason:Error)=>void;
 global.fetch=jest.fn<typeof fetch>().mockImplementation(()=>new Promise((_resolve,fail)=>{reject=fail;}));
 try{
  useAIOrderingStore.setState({messages:[],ackTimeouts:{},clearCart:jest.fn(),_sendInternalCommand:jest.fn(),fetchInitialSuggestions:jest.fn()});
  const old=useAIOrderingStore.getState()._postSupportChat('old',null);
  useAIOrderingStore.getState().resetChat();useAIOrderingStore.getState().resetChat();
  useAIOrderingStore.setState({isLoading:true,isProcessing:true});
  const current=useAIOrderingStore.getState().messages;
  reject(new Error('controlled late failure'));await old;
  expect(useAIOrderingStore.getState().messages).toEqual(current);
  expect(useAIOrderingStore.getState().isProcessing).toBe(true);
 }finally{useAIOrderingStore.setState(snapshot,true);global.fetch=before;}
});
