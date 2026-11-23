import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CustomerMemoryControls from '@/components/profile/CustomerMemoryControls';
import { api } from '@/lib/api';
jest.mock('@/lib/api', () => ({ api: { get:jest.fn(),put:jest.fn(),delete:jest.fn() } }));
const off={enabled:false,retention_days:90,preferences:[]};
beforeEach(() => {jest.clearAllMocks();jest.mocked(api.get).mockResolvedValue({data:off});});

it('is off until explicit enable, and explains the actual limited scope', async () => {
    render(<CustomerMemoryControls />);
    const enable=await screen.findByRole('button',{name:'Enable shopping memory'});
    expect(api.put).not.toHaveBeenCalled();
    expect(screen.getByText(/color, material and style/)).toBeInTheDocument();
    expect(screen.getByText(/90 days/)).toBeInTheDocument();
    jest.mocked(api.put).mockResolvedValue({data:{enabled:true}});
    jest.mocked(api.get).mockResolvedValue({data:{...off,enabled:true}});
    fireEvent.click(enable);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/users/me/memory/consent',{enabled:true}));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('is on'));
});

it('requires a second explicit confirmation before erasing, then reloads status', async () => {
    render(<CustomerMemoryControls />);
    fireEvent.click(await screen.findByRole('button',{name:'Turn off and erase preferences'}));
    expect(api.delete).not.toHaveBeenCalled();
    expect(screen.getByText(/does not delete chat history/)).toBeInTheDocument();
    jest.mocked(api.delete).mockResolvedValue({data:{deleted:true}});
    fireEvent.click(screen.getByRole('button',{name:'Confirm erase'}));
    await waitFor(() => expect(api.delete).toHaveBeenCalledWith('/users/me/memory'));
});

it('never shows a successful change when the backend outcome is uncertain', async () => {
    render(<CustomerMemoryControls />);
    const enable=await screen.findByRole('button',{name:'Enable shopping memory'});
    jest.mocked(api.put).mockRejectedValue(new Error('offline'));
    fireEvent.click(enable);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be confirmed');
    expect(screen.getByRole('button',{name:'Enable shopping memory'})).toBeDisabled();
    if(process.env.MEMORY_PREVIEW_HTML)require('fs').writeFileSync(process.env.MEMORY_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/cart-ui-preview.css"></head><body style="margin:0;background:#050505;font-family:Arial,sans-serif"><main style="max-width:430px;margin:auto;padding:16px">'+document.body.innerHTML+'</main></body></html>');
    fireEvent.click(screen.getByRole('button',{name:'Refresh settings'}));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
});

it('exports server-held preferences as readable JSON without sending another mutation', async () => {
    render(<CustomerMemoryControls />);
    fireEvent.click(await screen.findByRole('button',{name:'Export preferences'}));
    const text=await screen.findByLabelText('Your preferences export (JSON)');
    expect(text).toHaveValue(JSON.stringify(off,null,2));
    expect(api.put).not.toHaveBeenCalled();expect(api.delete).not.toHaveBeenCalled();
});

it('does not invent consent status when initial fetch fails', async () => {
    jest.mocked(api.get).mockRejectedValue(new Error('offline'));
    render(<CustomerMemoryControls />);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
    expect(screen.queryByRole('button',{name:'Enable shopping memory'})).not.toBeInTheDocument();
});
