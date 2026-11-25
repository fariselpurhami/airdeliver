import {useAIOrderingStore} from '@/hooks/useAIOrderingStore';

let snapshot:ReturnType<typeof useAIOrderingStore.getState>;
let fetchBefore:typeof fetch;
let socketBefore:typeof WebSocket;
class Socket {
  static OPEN=1;static CLOSED=3;static CONNECTING=0;
  static instances:Socket[]=[];
  readyState=0;
  onopen:(()=>void)|null=null;onclose:((event:CloseEvent)=>void)|null=null;onerror:(()=>void)|null=null;onmessage:unknown=null;
  constructor(public url:string){Socket.instances.push(this);}
  open(){this.readyState=1;this.onopen?.();}
  close(){this.readyState=3;this.onclose?.({code:1006} as CloseEvent);}
}
beforeEach(()=>{
  snapshot=useAIOrderingStore.getState();fetchBefore=global.fetch;socketBefore=global.WebSocket;
  jest.useFakeTimers();Socket.instances=[];
  global.WebSocket=Socket as unknown as typeof WebSocket;
  useAIOrderingStore.setState({socket:null,authToken:'valid-access-token',socketStatus:'disconnected',reconnectTimeoutId:null,reconnectAttempts:0,abortController:null,messageQueue:[],messages:[],isLoading:false,isProcessing:false});
});
afterEach(()=>{
  useAIOrderingStore.getState().disconnectSocket();
  jest.clearAllTimers();jest.useRealTimers();
  useAIOrderingStore.setState(snapshot,true);global.fetch=fetchBefore;global.WebSocket=socketBefore;
});

it('reconnects queued removal with stored access token, not an unreadable cookie',async()=>{
  const dispatch=jest.fn<(payload:Record<string,unknown>)=>Promise<void>>().mockResolvedValue(undefined);
  useAIOrderingStore.setState({_dispatchCommand:dispatch});
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({ticket:'opaque-ticket'})} as Response);
  useAIOrderingStore.getState().removeProductById(7);
  await Promise.resolve();await Promise.resolve();
  expect(global.fetch).toHaveBeenCalledWith('/api/v1/ai-ordering/ticket',expect.objectContaining({headers:expect.objectContaining({Authorization:'Bearer valid-access-token'})}));
  expect(dispatch).not.toHaveBeenCalled();
  Socket.instances[0]!.open();
  await jest.advanceTimersByTimeAsync(501);
  expect(dispatch.mock.calls.filter(([p])=>p.message==='__INTERNAL_REMOVE_BY_ID__:7')).toHaveLength(1);
  expect(useAIOrderingStore.getState().messageQueue).toHaveLength(0);
});

it('schedules bounded reconnect on close and explicit disconnect cancels it',async()=>{
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({ticket:'opaque-ticket'})} as Response);
  await useAIOrderingStore.getState().connectSocket('valid-access-token');
  Socket.instances[0]!.open();Socket.instances[0]!.close();
  expect(useAIOrderingStore.getState().reconnectTimeoutId).not.toBeNull();
  await jest.advanceTimersByTimeAsync(1001);
  expect(Socket.instances).toHaveLength(2);
  useAIOrderingStore.getState().disconnectSocket();
  const before=jest.mocked(global.fetch).mock.calls.length;
  await jest.advanceTimersByTimeAsync(30000);
  expect(global.fetch).toHaveBeenCalledTimes(before);
  expect(useAIOrderingStore.getState().authToken).toBeNull();
});

it('flushes unsent commands sequentially and retains the unsent tail after disconnect',async()=>{
  const socket={readyState:1} as WebSocket;
  const commands=[{message:'__INTERNAL_ADD_BY_ID__:7'},{message:'__INTERNAL_REMOVE_BY_ID__:7'}];
  let finish!:()=>void;
  const dispatch=jest.fn<(payload:Record<string,unknown>)=>Promise<void>>().mockImplementationOnce(()=>new Promise<void>(r=>{finish=r;})).mockResolvedValue(undefined);
  useAIOrderingStore.setState({socket,messageQueue:commands,_dispatchCommand:dispatch});
  const flushing=useAIOrderingStore.getState().processOfflineQueue();
  expect(dispatch).toHaveBeenCalledTimes(1);
  useAIOrderingStore.setState({socket:null});finish();await flushing;
  expect(dispatch).toHaveBeenCalledTimes(1);
  expect(useAIOrderingStore.getState().messageQueue).toEqual([commands[1]]);
});


it('renews a single-use ticket for every reconnect attempt',async()=>{
  useAIOrderingStore.setState({_dispatchCommand:jest.fn<(payload:Record<string,unknown>)=>Promise<void>>().mockResolvedValue(undefined)});
  global.fetch=jest.fn<typeof fetch>()
    .mockResolvedValueOnce({ok:true,json:async()=>({ticket:'first-ticket'})} as Response)
    .mockResolvedValueOnce({ok:true,json:async()=>({ticket:'second-ticket'})} as Response);
  await useAIOrderingStore.getState().connectSocket('valid-access-token');
  Socket.instances[0]!.open();Socket.instances[0]!.close();
  await jest.advanceTimersByTimeAsync(1001);
  expect(Socket.instances[0]!.url).toContain('first-ticket');
  expect(Socket.instances[1]!.url).toContain('second-ticket');
});

it('caps transient ticket retries and does not retry denied authentication',async()=>{
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:false,status:503} as Response);
  await useAIOrderingStore.getState().connectSocket('valid-access-token');
  await jest.advanceTimersByTimeAsync(120000);
  expect(global.fetch).toHaveBeenCalledTimes(6);
  expect(useAIOrderingStore.getState().reconnectTimeoutId).toBeNull();
  useAIOrderingStore.setState({reconnectAttempts:0});
  jest.mocked(global.fetch).mockClear().mockResolvedValue({ok:false,status:401} as Response);
  await useAIOrderingStore.getState().connectSocket('valid-access-token');
  await jest.advanceTimersByTimeAsync(120000);
  expect(global.fetch).toHaveBeenCalledTimes(1);
});


it('bounds a stalled socket handshake and cancels pending work on signout',async()=>{
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({ticket:'ticket'})} as Response);
  await useAIOrderingStore.getState().connectSocket('valid-access-token');
  expect(useAIOrderingStore.getState().socketStatus).toBe('connecting');
  await jest.advanceTimersByTimeAsync(10001);
  expect(Socket.instances[0]!.readyState).toBe(Socket.CLOSED);
  expect(useAIOrderingStore.getState().reconnectTimeoutId).not.toBeNull();
  useAIOrderingStore.getState().disconnectSocket();
  await jest.advanceTimersByTimeAsync(30000);
  expect(Socket.instances).toHaveLength(1);
});
