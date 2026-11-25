import React from 'react';
import {render,screen} from '@testing-library/react';
import{AISecuredOrdersBadge}from'@/components/hero/AISecuredOrdersBadge';
it('preserves the framed default for all non-home callers',()=>{
 render(<AISecuredOrdersBadge/>);
 expect(screen.getByText('AI-SECURED ORDERS').parentElement).toHaveClass('rounded-full','border','bg-[#0D0D0C]/80');
});
it('home opt-in removes every capsule surface without changing copy',()=>{
 render(<AISecuredOrdersBadge unframed/>);
 const container=screen.getByText('AI-SECURED ORDERS').parentElement!;
 for(const token of ['rounded-full','border','border-white/10','bg-[#0D0D0C]/80','backdrop-blur-xl','shadow-2xl'])expect(container).not.toHaveClass(token);
 expect(container.querySelector('.bg-cyan-400')).toBeInTheDocument();
});
