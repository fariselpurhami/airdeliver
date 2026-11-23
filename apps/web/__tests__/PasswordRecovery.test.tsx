import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import PasswordRecoveryForm from '@/components/PasswordRecoveryForm';
import {api} from '@/lib/api';
import {signOut} from 'next-auth/react';
jest.mock('@/lib/api',()=>({api:{post:jest.fn()}}));
jest.mock('next-auth/react',()=>({signOut:jest.fn()}));
beforeEach(()=>{jest.clearAllMocks();window.history.replaceState(null,'','/forgot-password');});
it('requests recovery from real endpoint with generic response',async()=>{
 jest.mocked(api.post).mockResolvedValue({data:{message:'If an eligible account exists, a reset link will be sent.'}});
 render(<PasswordRecoveryForm/>);fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'test@example.com'}});fireEvent.click(screen.getByRole('button',{name:'Send reset link'}));
 await waitFor(()=>expect(screen.getByRole('status')).toBeInTheDocument());expect(api.post).toHaveBeenCalledWith('/auth/password-reset/request',{email:'test@example.com'});
});
it('takes token from fragment, removes URL secret and signs out after successful reset',async()=>{
 window.history.replaceState(null,'','/reset-password#token=fixture-reset-token');
 jest.mocked(api.post).mockResolvedValue({data:{message:'Password updated. Sign in again.'}});
 render(<PasswordRecoveryForm reset/>);expect(window.location.hash).toBe('');
 fireEvent.change(screen.getByLabelText('New password'),{target:{value:'new-fixture-password'}});fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'new-fixture-password'}});fireEvent.click(screen.getByRole('button',{name:'Update password'}));
 await waitFor(()=>expect(signOut).toHaveBeenCalledWith({redirect:false}));expect(api.post).toHaveBeenCalledWith('/auth/password-reset/confirm',{token:'fixture-reset-token',password:'new-fixture-password'});
});
it('does not call reset without its credential',()=>{
 render(<PasswordRecoveryForm reset/>);fireEvent.change(screen.getByLabelText('New password'),{target:{value:'new-fixture-password'}});fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'new-fixture-password'}});fireEvent.click(screen.getByRole('button',{name:'Update password'}));
 expect(screen.getByRole('alert')).toHaveTextContent('missing its token');expect(api.post).not.toHaveBeenCalled();
});
