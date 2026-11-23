// apps/web/__tests__/useAIOrderingStore.test.ts
//
// Pins the rewired assistant path: chat text and image uploads go to the
// live ai_support HTTP endpoint; cart/checkout commands go to the HTTP
// ai-ordering endpoints; the websocket is receive-only for AI responses.

import type * as JestGlobals from '@jest/globals';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
import { getCheckoutRequestKey } from '@/lib/checkout-request';
jest.mock('@/lib/checkout-request',()=>({getCheckoutRequestKey:jest.fn(),retireCheckoutRequestKey:jest.fn()}));

type StoreSnapshot = ReturnType<typeof useAIOrderingStore.getState>;

let snapshot: StoreSnapshot;

const resetStore = () => {
  useAIOrderingStore.setState({
    messages: [],
    isLoading: false,
    isProcessing: false,
    ackTimeouts: {},
    socketStatus: 'disconnected',
  } as Partial<StoreSnapshot>);
};

beforeEach(() => {
  snapshot = useAIOrderingStore.getState();
  resetStore();
});

afterEach(() => {
  // Clear any pending ACK timeouts, then restore the untouched store.
  const pending = useAIOrderingStore.getState().ackTimeouts;
  Object.values(pending).forEach((t) => clearTimeout(t));
  useAIOrderingStore.setState(snapshot, true);
  jest.restoreAllMocks();
});

describe('sendMessage routing', () => {
  it('sends chat text to the HTTP assistant endpoint, not the socket', () => {
    const postSpy = jest.fn<(message: string, msgId: string | null, imageBase64?: string) => Promise<void>>().mockResolvedValue(undefined);
    const socketSpy = jest.fn();
    useAIOrderingStore.setState({
      _postSupportChat: postSpy,
      _sendInternalCommand: socketSpy,
    } as Partial<StoreSnapshot>);

    useAIOrderingStore.getState().sendMessage('Do you have wireless headphones?');

    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy.mock.calls[0]?.[0]).toBe('Do you have wireless headphones?');
    expect(socketSpy).not.toHaveBeenCalled();
  });

  it('routes silent cart/checkout commands through the internal command path', () => {
    const postSpy = jest.fn<(message: string, msgId: string | null, imageBase64?: string) => Promise<void>>().mockResolvedValue(undefined);
    const socketSpy = jest.fn();
    useAIOrderingStore.setState({
      _postSupportChat: postSpy,
      _sendInternalCommand: socketSpy,
    } as Partial<StoreSnapshot>);

    useAIOrderingStore.getState().sendMessage('checkout', true);

    expect(socketSpy).toHaveBeenCalledTimes(1);
    expect(postSpy).not.toHaveBeenCalled();
  });
});

describe('_postSupportChat', () => {
  it('marks the user message sent and appends the assistant reply', async () => {
    global.fetch = jest.fn<typeof fetch>().mockResolvedValue({
      ok: true,
      json: async () => ({ text: 'Yes, the Volt Headphones are in stock.' }),
    } as Response);

    useAIOrderingStore.setState({
      messages: [
        { id: 1, msgId: 'msg-1', sender: 'user', contentType: 'text', content: 'hello', status: 'sending' },
        { id: 2, sender: 'ai', contentType: 'typing', content: null },
      ],
      isLoading: true,
    } as Partial<StoreSnapshot>);

    await useAIOrderingStore.getState()._postSupportChat('hello', 'msg-1');

    const state = useAIOrderingStore.getState();
    const userMsg = state.messages.find((m) => m.msgId === 'msg-1');
    expect(userMsg?.status).toBe('sent');
    expect(state.messages.some((m) => m.contentType === 'typing')).toBe(false);
    expect(
      state.messages.some(
        (m) => m.sender === 'ai' && m.content === 'Yes, the Volt Headphones are in stock.'
      )
    ).toBe(true);

    const [url, init] = (global.fetch as unknown as ReturnType<typeof JestGlobals.jest.fn>).mock.calls[0]!;
    expect(url).toBe('/api/v1/ai-support/chat');
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.message).toBe('hello');
    expect(typeof body.session_id).toBe('string');
    expect(body.session_id.length).toBeGreaterThanOrEqual(8);
  });

  it('marks the message failed and posts an honest error on HTTP failure', async () => {
    global.fetch = jest.fn<typeof fetch>().mockRejectedValue(new Error('network down'));

    useAIOrderingStore.setState({
      messages: [
        { id: 1, msgId: 'msg-2', sender: 'user', contentType: 'text', content: 'hello', status: 'sending' },
      ],
      isLoading: true,
    } as Partial<StoreSnapshot>);

    await useAIOrderingStore.getState()._postSupportChat('hello', 'msg-2');

    const state = useAIOrderingStore.getState();
    expect(state.messages.find((m) => m.msgId === 'msg-2')?.status).toBe('failed');
    expect(
      state.messages.some((m) => m.contentType === 'error' && typeof m.content === 'string')
    ).toBe(true);
    expect(state.isLoading).toBe(false);
  });
});

describe('sendImage', () => {
  it('routes image uploads to the HTTP visual-search path', () => {
    const postSpy = jest.fn<(message: string, msgId: string | null, imageBase64?: string) => Promise<void>>().mockResolvedValue(undefined);
    const socketSpy = jest.fn();
    useAIOrderingStore.setState({
      _postSupportChat: postSpy,
      _sendInternalCommand: socketSpy,
    } as Partial<StoreSnapshot>);

    useAIOrderingStore.getState().sendImage('data:image/png;base64,AAA', 'AAA', 'what is this?');

    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy.mock.calls[0]?.[0]).toBe('what is this?');
    expect(postSpy.mock.calls[0]?.[2]).toBe('AAA');
    expect(socketSpy).not.toHaveBeenCalled();
  });
});

describe('_dispatchCommand', () => {
  const run = (payload: Record<string, unknown>) => {
    const postSpy = jest.fn<(path: string, body?: Record<string, unknown>) => Promise<boolean>>().mockResolvedValue(true);
    useAIOrderingStore.setState({ _postCartCommand: postSpy } as Partial<StoreSnapshot>);
    return { postSpy, done: useAIOrderingStore.getState()._dispatchCommand(payload) };
  };

  it('maps add-by-id to POST /cart/add', async () => {
    const { postSpy, done } = run({ message: '__INTERNAL_ADD_BY_ID__:42' });
    await done;
    expect(postSpy).toHaveBeenCalledWith('/cart/add', { product_id: 42 });
  });

  it('maps remove-by-id to POST /cart/remove', async () => {
    const { postSpy, done } = run({ message: '__INTERNAL_REMOVE_BY_ID__:7' });
    await done;
    expect(postSpy).toHaveBeenCalledWith('/cart/remove', { product_id: 7 });
  });

  it('maps clear cart phrases to POST /cart/clear', async () => {
    const { postSpy, done } = run({ message: 'clear cart' });
    await done;
    expect(postSpy).toHaveBeenCalledWith('/cart/clear', {});
  });

  it('collects shipping before sending any checkout payment request', async () => {
    for (const message of ['__INTERNAL_CONFIRM_ORDER__', 'checkout', 'pay now', 'retry payment']) {
      const postSpy = jest.fn<(path: string, body?: Record<string, unknown>) => Promise<boolean>>().mockResolvedValue(true);
      useAIOrderingStore.setState({ _postCartCommand: postSpy } as Partial<StoreSnapshot>);
      await useAIOrderingStore.getState()._dispatchCommand({ message });
      expect(postSpy).not.toHaveBeenCalled();
      expect(useAIOrderingStore.getState().isShippingStep).toBe(true);
    }
  });

  it('maps cancel intent to POST /checkout/cancel with the order id', async () => {
    const { postSpy, done } = run({ type: 'CANCEL_INTENT', message: { orderId: 9, reason: 'changed_mind' } });
    await done;
    expect(postSpy).toHaveBeenCalledWith('/checkout/cancel', { order_id: 9 });
  });

  it('maps reset session to POST /session/reset', async () => {
    const { postSpy, done } = run({ message: '__INTERNAL_RESET_SESSION__' });
    await done;
    expect(postSpy).toHaveBeenCalledWith('/session/reset', {});
  });

  it('maps initial suggestions to POST /session/suggestions', async () => {
    const { postSpy, done } = run({ message: '__INTERNAL_GET_INITIAL_SUGGESTIONS__' });
    await done;
    expect(postSpy).toHaveBeenCalledWith('/session/suggestions', {});
  });

  it('drops the one command with no live backend instead of faking an ACK', async () => {
    const { postSpy, done } = run({ message: '__INTERNAL_INITIATE_RECOVERY__' });
    await done;
    expect(postSpy).not.toHaveBeenCalled();
  });

  it('keeps suggestion-fetch failure silent (best-effort hydration)', async () => {
    const postSpy = jest.fn<(path: string, body?: Record<string, unknown>) => Promise<boolean>>().mockResolvedValue(false);
    useAIOrderingStore.setState({ _postCartCommand: postSpy } as Partial<StoreSnapshot>);
    await useAIOrderingStore.getState()._dispatchCommand({ message: '__INTERNAL_GET_INITIAL_SUGGESTIONS__' });
    const state = useAIOrderingStore.getState();
    expect(state.messages.some((m) => m.contentType === 'error')).toBe(false);
  });

  it('surfaces an honest error when the command request fails', async () => {
    const postSpy = jest.fn<(path: string, body?: Record<string, unknown>) => Promise<boolean>>().mockResolvedValue(false);
    useAIOrderingStore.setState({ _postCartCommand: postSpy, isLoading: true } as Partial<StoreSnapshot>);
    await useAIOrderingStore.getState()._dispatchCommand({ message: '__INTERNAL_CLEAR_CART__' });
    const state = useAIOrderingStore.getState();
    expect(state.isLoading).toBe(false);
    expect(state.messages.some((m) => m.contentType === 'error')).toBe(true);
  });
});

describe('handleSocketMessage', () => {
  it('surfaces backend ERROR frames as visible error messages', () => {
    useAIOrderingStore.setState({
      messages: [
        { id: 1, sender: 'ai', contentType: 'typing', content: null },
      ],
      isLoading: true,
      isProcessing: true,
    } as Partial<StoreSnapshot>);

    useAIOrderingStore.getState().handleSocketMessage({
      type: 'ERROR',
      code: 'DELIVERY_FAILED',
      content: 'Service temporarily unavailable. Please try again.',
    });

    const state = useAIOrderingStore.getState();
    expect(state.messages.some((m) => m.contentType === 'typing')).toBe(false);
    expect(
      state.messages.some(
        (m) => m.contentType === 'error' && m.content === 'Service temporarily unavailable. Please try again.'
      )
    ).toBe(true);
    expect(state.isLoading).toBe(false);
    expect(state.isProcessing).toBe(false);
  });
});

describe('checkout HTTP reconciliation',()=>{
  beforeEach(()=>{
    jest.mocked(getCheckoutRequestKey).mockResolvedValue('a02cf0a7-67a1-4dcc-96d6-45b7be67d306');
    useAIOrderingStore.setState({authToken:'real-backend-token'});
  });
  it('sends bearer and idempotency headers and accepts a direct handoff without a socket',async()=>{
    const payment={checkout_request_id:'a02cf0a7-67a1-4dcc-96d6-45b7be67d306',gateway_provider:'stripe',client_secret:'test-secret',order_data:{order_id:7,total:21,items:[],currency:'USD'}};
    global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({status:'ready',payment})} as Response);
    expect(await useAIOrderingStore.getState()._postCartCommand('/checkout/confirm',{})).toBe(true);
    const headers=(jest.mocked(global.fetch).mock.calls[0]![1] as RequestInit).headers as Record<string,string>;
    expect(headers.Authorization).toBe('Bearer real-backend-token');
    expect(headers['Idempotency-Key']).toBe('a02cf0a7-67a1-4dcc-96d6-45b7be67d306');
    expect(useAIOrderingStore.getState().paymentDetails).toEqual(payment);
  });
  it('keeps an accepted-but-unconfirmed checkout open rather than showing success',async()=>{
    global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({status:'pending',order_id:7})} as Response);
    expect(await useAIOrderingStore.getState()._postCartCommand('/checkout/confirm',{})).toBe(false);
  });
  it('shows refreshed catalog prices even when the socket misses the update',async()=>{
    global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:false,json:async()=>({status:'review_required',cart:{items:[{product_id:7,name:'Shoes',price:'12.50',quantity:2}],total:'25.00'}})} as Response);
    expect(await useAIOrderingStore.getState()._postCartCommand('/checkout/confirm',{})).toBe(true);
    expect(useAIOrderingStore.getState().messages.some(m=>m.contentType==='cart_preview')).toBe(true);
  });
});


it('ignores a delayed payment handoff from a different checkout request',()=>{
  useAIOrderingStore.setState({activeCheckoutRequestId:'current-request',paymentDetails:null});
  useAIOrderingStore.getState().addSocketAIMessage({type:'payment_intent',content:{checkout_request_id:'older-request',client_secret:'wrong-order'}});
  expect(useAIOrderingStore.getState().paymentDetails).toBeNull();
});

describe('reviewed action safety',()=>{
 it('does not execute clear-cart text inside a negated customer sentence',()=>{
  const chat=jest.fn<(message:string,msgId:string|null,imageBase64?:string)=>Promise<void>>().mockResolvedValue(undefined),command=jest.fn();
  useAIOrderingStore.setState({_postSupportChat:chat,_sendInternalCommand:command});
  useAIOrderingStore.getState().sendMessage('do not clear cart, just show me my items');
  expect(chat).toHaveBeenCalled();expect(command).not.toHaveBeenCalled();
 });
 it('preserves structured response action for the ordering UI instead of dropping it',async()=>{
  const action={action:'track_order',payload:{order_id:'7'}};
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({text:'Review order',action})} as Response);
  await useAIOrderingStore.getState()._postSupportChat('track7',null);
  expect(useAIOrderingStore.getState().messages.at(-1)?.action).toEqual(action);
 });
});

describe('specific cancellation outcome',()=>{
 it('keeps payment context and cart on unconfirmed cancellation',async()=>{
  const details={orderId:7} as any;
  useAIOrderingStore.setState({authToken:'fixture',paymentDetails:details,recoveryOrderDetails:details,recoveryMode:true});
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:false,json:async()=>({status:'provider_reconciliation_required'})} as Response);
  await useAIOrderingStore.getState().hardCancelOrder('changed_mind');
  expect(useAIOrderingStore.getState().paymentDetails).toEqual(details);
  expect(useAIOrderingStore.getState().recoveryMode).toBe(true);
  expect(useAIOrderingStore.getState().messages.at(-1)?.content).toContain('not confirmed');
 });
 it('clears payment context only after explicit cancellation response',async()=>{
  const details={orderId:7} as any;
  useAIOrderingStore.setState({authToken:'fixture',paymentDetails:details,recoveryOrderDetails:details,recoveryMode:true});
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({status:'cancelled',order_id:7})} as Response);
  await useAIOrderingStore.getState().hardCancelOrder('changed_mind');
  expect(useAIOrderingStore.getState().paymentDetails).toBeNull();
  expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0]?.[1]?.body))).toEqual({order_id:7});
 });
});

it('shows an honest pending cart message without claiming the item was added',()=>{
  const send=jest.fn();
  useAIOrderingStore.setState({_sendInternalCommand:send} as Partial<StoreSnapshot>);
  useAIOrderingStore.getState().addProductById({id:7},'product-7');
  expect(send).toHaveBeenCalledWith('__INTERNAL_ADD_BY_ID__:7');
  expect(useAIOrderingStore.getState().messages.some(m=>typeof m.content==='string'&&m.content.includes('Waiting for cart confirmation'))).toBe(true);
  expect(useAIOrderingStore.getState().messages.some(m=>typeof m.content==='string'&&m.content.includes('added to your cart'))).toBe(false);
});
