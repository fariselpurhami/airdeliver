// apps/web/__tests__/useAIOrderingStore.test.ts
//
// Pins the rewired assistant path: chat text and image uploads go to the
// live ai_support HTTP endpoint; silent cart/checkout commands stay on the
// websocket.

import type * as JestGlobals from '@jest/globals';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';

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

  it('keeps silent cart/checkout commands on the socket', () => {
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
