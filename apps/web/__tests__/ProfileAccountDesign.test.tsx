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
 fireEvent.click(screen.getByRole('button',{name:'Update'}));
 expect(screen.getByText('The passwords do not match.')).toBeVisible();
 fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'short'}});
 fireEvent.click(screen.getByRole('button',{name:'Update'}));
 expect(screen.getByText('Use a password with at least 8 characters.')).toBeVisible();
 expect(onSave).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Current password'),{target:{value:'old-preview'}});
 fireEvent.change(screen.getByLabelText('New password'),{target:{value:'new-preview'}});
 fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'new-preview'}});
 fireEvent.click(screen.getByRole('button',{name:'Update'}));
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
