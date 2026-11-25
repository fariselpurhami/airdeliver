import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CartPage from '@/app/(main)/cart/page';
import { useCartStore } from '@/hooks/useCartStore';
import { api } from '@/lib/api';

jest.mock('@/lib/api', () => ({ api: { post: jest.fn(), get: jest.fn() } }));
jest.mock('@react-three/fiber', () => ({ Canvas: () => null, useFrame: jest.fn() }));
jest.mock('@react-three/drei', () => ({ Stars: () => null }));
jest.mock('next/image', () => ({ __esModule:true, default: (props: any) => <img alt={props.alt} /> }));
jest.mock('framer-motion', () => {
    const React = require('react');
    const tags = new Map();
    return { AnimatePresence: ({children}:any) => children, motion:new Proxy({}, {get:(_,tag) => {
        if (!tags.has(tag)) tags.set(tag, React.forwardRef(({children,initial,animate,exit,transition,layout,whileHover,whileTap,...props}:any,ref:any) => React.createElement(tag,{...props,ref},children)));
        return tags.get(tag);
    }}) };
});
const item={id:7,name:'Atlas Headphones',price:49,quantity:1,image_url:null,description:'',inventory:5};
beforeEach(() => { jest.clearAllMocks();useCartStore.setState({items:[item]});jest.mocked(api.get).mockResolvedValueOnce({data:{items:[{product_id:7,name:item.name,quantity:1,price:'49.00'}]}}); });

it('keeps the item while removal is pending, and only removes after acknowledgement', async () => {
    let resolve!: (data:any) => void;
    jest.mocked(api.post).mockImplementation(() => new Promise(r => {resolve=r;}));
    render(<CartPage />);
    const remove=await screen.findByRole('button',{name:'Remove Atlas Headphones'});
    await waitFor(() => expect(remove).toBeEnabled());
    fireEvent.click(remove);
    expect(useCartStore.getState().items).toHaveLength(1);
    expect(remove).toBeDisabled();
    expect(screen.getByRole('button',{name:/Proceed to Checkout/i})).toBeDisabled();
    resolve({data:{status:'accepted'}});
    await waitFor(() => expect(useCartStore.getState().items).toHaveLength(0));
    expect(api.post).toHaveBeenCalledTimes(1);
});

it('keeps items on an uncertain failure and refreshes authoritative cart before allowing checkout', async () => {
    jest.mocked(api.post).mockRejectedValue(new Error('timeout'));
    jest.mocked(api.get).mockResolvedValue({data:{items:[]}});
    render(<CartPage />);
    const remove=await screen.findByRole('button',{name:'Remove Atlas Headphones'});
    await waitFor(() => expect(remove).toBeEnabled());
    fireEvent.click(remove);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not confirm');
    expect(useCartStore.getState().items).toHaveLength(1);
    expect(screen.getByRole('button',{name:/Proceed to Checkout/i})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Refresh cart'}));
    await waitFor(() => expect(useCartStore.getState().items).toHaveLength(0));
    expect(api.get).toHaveBeenCalledWith('/ai-ordering/cart');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(api.post).toHaveBeenCalledTimes(1);
});

it('clear failure preserves the whole cart and shows a visible error', async () => {
    jest.mocked(api.post).mockRejectedValue(new Error('offline'));
    render(<CartPage />);
    const clear=await screen.findByRole('button',{name:'Clear Cart'});
    await waitFor(() => expect(clear).toBeEnabled());
    fireEvent.click(clear);
    await screen.findByRole('alert');
    if (process.env.CART_PREVIEW_HTML) require('fs').writeFileSync(process.env.CART_PREVIEW_HTML, '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/cart-ui-preview.css"></head><body style="margin:0">'+document.body.innerHTML+'</body></html>');
    expect(useCartStore.getState().items).toHaveLength(1);
    expect(api.post).toHaveBeenCalledWith('/ai-ordering/cart/clear');
});

it('failed or malformed refresh cannot silently erase preserved items', async () => {
    jest.mocked(api.post).mockRejectedValue(new Error('offline'));
    jest.mocked(api.get).mockResolvedValue({data:{items:[{product_id:'bad'}]}});
    render(<CartPage />);
    const clear=await screen.findByRole('button',{name:'Clear Cart'});
    await waitFor(() => expect(clear).toBeEnabled());
    fireEvent.click(clear);
    await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button',{name:'Refresh cart'}));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('could not refresh'));
    expect(useCartStore.getState().items).toHaveLength(1);
});
