import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {ChangePasswordModal,EditProfileDetailsModal,ViewOrdersModal} from '@/components/profile/ProfileModals';
import useSWR from 'swr';
jest.mock('swr');
const swr=jest.mocked(useSWR);
beforeEach(()=>{jest.clearAllMocks();swr.mockReturnValue({data:{orders:[],total:0,page:1,limit:10},isLoading:false,error:null} as any);});
it('preserves changed-field-only profile save',async()=>{
 const onSave=jest.fn(async (..._args: any[]) => {});
 render(<EditProfileDetailsModal isOpen onClose={jest.fn()} userData={{full_name:'Existing name',phone_number:'123',address:'Existing address'}} onSave={onSave}/>);
 expect(screen.getByRole('heading',{name:'Edit profile'})).toBeVisible();
 fireEvent.change(screen.getByLabelText('Full Name'),{target:{value:'Updated name'}});
 fireEvent.click(screen.getByRole('button',{name:'Save'}));
 await waitFor(()=>expect(onSave).toHaveBeenCalledWith({full_name:'Updated name'}));
});
it('does not save profile when cancel is selected',()=>{
 const onSave=jest.fn(async (..._args: any[]) => {}),onClose=jest.fn();
 render(<EditProfileDetailsModal isOpen onClose={onClose} userData={{full_name:'Existing name'}} onSave={onSave}/>);
 fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
 expect(onClose).toHaveBeenCalledTimes(1);expect(onSave).not.toHaveBeenCalled();
});
it('retains password match and length checks before submitting',async()=>{
 const onSave=jest.fn(async (..._args: any[]) => {});
 render(<ChangePasswordModal isOpen onClose={jest.fn()} onSave={onSave}/>);
 fireEvent.change(screen.getByLabelText('New password'),{target:{value:'short'}});
 fireEvent.click(screen.getByRole('button',{name:'Change password'}));
 expect(screen.getByText('The passwords do not match.')).toBeVisible();
 fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'short'}});
 fireEvent.click(screen.getByRole('button',{name:'Change password'}));
 expect(screen.getByText('Use a password with at least 8 characters.')).toBeVisible();
 expect(onSave).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Current password'),{target:{value:'old-preview'}});
 fireEvent.change(screen.getByLabelText('New password'),{target:{value:'new-preview'}});
 fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'new-preview'}});
 fireEvent.click(screen.getByRole('button',{name:'Change password'}));
 await waitFor(()=>expect(onSave).toHaveBeenCalledWith('old-preview','new-preview'));
});
it('keeps real empty order history without invented entries',()=>{
 render(<ViewOrdersModal isOpen onClose={jest.fn()}/>);
 expect(screen.getByRole('heading',{name:'Your orders'})).toBeVisible();
 expect(screen.getByText('You have no orders yet.')).toBeVisible();
 expect(screen.queryByRole('table')).not.toBeInTheDocument();
});
it('preserves tracking links, currency and pagination for returned orders',()=>{
 swr.mockReturnValue({data:{orders:[{id:42,user_id:1,status:'processing',total_price:25,currency:'EUR',created_at:'2026-11-25T08:00:00Z'}],total:11,page:1,limit:10},isLoading:false,error:null} as any);
 render(<ViewOrdersModal isOpen onClose={jest.fn()}/>);
 expect(screen.getByRole('link',{name:'View order 42'})).toHaveAttribute('href','/tracking/42');
 expect(screen.getByText(/EUR/)).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:/NEXT/}));
 expect(swr).toHaveBeenLastCalledWith('/orders/me?page=2&limit=10',expect.any(Function),expect.objectContaining({keepPreviousData:true}));
});

it('names the password dialog and supports Escape with focus restoration',async()=>{
 const close=jest.fn();
 const launcher=document.createElement('button');document.body.appendChild(launcher);launcher.focus();
 const view=render(<ChangePasswordModal isOpen onClose={close} onSave={async()=>{}}/>);
 const dialog=screen.getByRole('dialog',{name:'Change your password'});
 await waitFor(()=>expect(dialog).toHaveFocus());
 fireEvent.keyDown(document,{key:'Tab'});
 expect(screen.getByRole('button',{name:'Close modal'})).toHaveFocus();
 fireEvent.keyDown(document,{key:'Escape'});expect(close).toHaveBeenCalled();
 view.unmount();expect(launcher).toHaveFocus();launcher.remove();
});
it('prevents repeated saves and shows a failed save without closing',async()=>{
 let reject: (reason:Error)=>void=()=>{};
 const onSave=jest.fn(()=>new Promise<void>((_,r)=>{reject=r})),close=jest.fn();
 render(<EditProfileDetailsModal isOpen onClose={close} userData={{full_name:'Existing'}} onSave={onSave}/>);
 fireEvent.change(screen.getByLabelText('Full Name'),{target:{value:'New'}});
 fireEvent.click(screen.getByRole('button',{name:'Save'}));
 const busy=screen.getByRole('button',{busy:true});expect(busy).toBeDisabled();
 fireEvent.click(busy);expect(onSave).toHaveBeenCalledTimes(1);
 reject(new Error('offline'));expect(await screen.findByRole('alert')).toHaveTextContent("couldn't be confirmed");
 expect(close).not.toHaveBeenCalled();
});
it('never shows empty-history success during an order fetch failure',()=>{
 swr.mockReturnValue({data:{orders:[],total:0},isLoading:false,error:new Error('offline')} as any);
 render(<ViewOrdersModal isOpen onClose={jest.fn()}/>);
 expect(screen.getByText('Order history is unavailable')).toBeVisible();
 expect(screen.queryByText('You have no orders yet.')).not.toBeInTheDocument();
});
it('retains usable password autocomplete and accessible visibility toggles',()=>{
 render(<ChangePasswordModal isOpen onClose={jest.fn()} onSave={async()=>{}}/>);
 expect(screen.getByLabelText('Current password')).toHaveAttribute('autocomplete','current-password');
 expect(screen.getByLabelText('New password')).toHaveAttribute('autocomplete','new-password');
 const toggle=screen.getAllByRole('button',{name:'Show password'})[0]!;
 fireEvent.click(toggle);expect(screen.getByLabelText('Current password')).toHaveAttribute('type','text');
 fireEvent.click(screen.getByRole('button',{name:'Hide password'}));expect(screen.getByLabelText('Current password')).toHaveAttribute('type','password');
});
