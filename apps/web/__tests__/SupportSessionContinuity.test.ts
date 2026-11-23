import {useAIOrderingStore} from '@/hooks/useAIOrderingStore';

it('does not reattach invisible localStorage history to a new visible chat',()=>{
  window.localStorage.setItem('airdeliver-support-session','old-invisible-session');
  const first=useAIOrderingStore.getState()._getSupportSessionId();
  expect(first).not.toBe('old-invisible-session');
  expect(useAIOrderingStore.getState()._getSupportSessionId()).toBe(first);
});

it('rotates the support identity when visible chat is reset, preserving old reset dispatch',()=>{
  const snapshot=useAIOrderingStore.getState();
  const first=snapshot._getSupportSessionId();
  const command=jest.fn();
  try {
    useAIOrderingStore.setState({clearCart:jest.fn(),_sendInternalCommand:command,fetchInitialSuggestions:jest.fn()});
    useAIOrderingStore.getState().resetChat();
    expect(useAIOrderingStore.getState()._getSupportSessionId()).not.toBe(first);
    expect(command).toHaveBeenCalledWith('__INTERNAL_RESET_SESSION__',{},true);
  } finally {useAIOrderingStore.setState(snapshot,true);}
});
