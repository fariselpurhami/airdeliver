import { registerAccount, safeCallbackPath } from '@/lib/auth-flow';
import { api } from '@/lib/api';
jest.mock('@/lib/api',()=>({api:{post:jest.fn()}}));
it('registers through the real public endpoint without choosing privileges',async()=>{
  jest.mocked(api.post).mockResolvedValue({data:{id:1}});
  await registerAccount({email:'buyer@example.com',password:'valid-password',fullName:'Buyer'});
  expect(api.post).toHaveBeenCalledWith('/users/',{email:'buyer@example.com',password:'valid-password',full_name:'Buyer'});
});
it.each(['https://evil.test','//evil.test','/\\evil.test','javascript:alert(1)'])('rejects unsafe callback %s',value=>expect(safeCallbackPath(value)).toBe('/'));
it('keeps a same-origin checkout callback',()=>expect(safeCallbackPath('/checkout?step=delivery')).toBe('/checkout?step=delivery'));
