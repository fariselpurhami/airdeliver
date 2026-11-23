import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import CheckoutForm from '@/components/checkout/CheckoutForm';
import AIPaymentForm from '@/components/ai/AIPaymentForm';
const confirmPayment=jest.fn<(...args: any[]) => Promise<any>>();
const elements={};
jest.mock('@stripe/react-stripe-js',()=>({
 useStripe:()=>({confirmPayment}),useElements:()=>elements,
 PaymentElement:()=> <div data-testid="stripe-payment-element"/>
}));
beforeEach(()=>{jest.clearAllMocks();});
it('keeps standard checkout confirmPayment and return URL contract',async()=>{
 confirmPayment.mockResolvedValue({error:{type:'card_error',message:'Card rejected fixture'}});
 render(<CheckoutForm/>);
 fireEvent.click(screen.getByText('Pay now'));
 await waitFor(()=>expect(screen.getByText('Card rejected fixture')).toBeInTheDocument());
 expect(confirmPayment).toHaveBeenCalledWith({elements,confirmParams:{return_url:window.location.origin+'/profile'}});
});
it('keeps assistant checkout non-redirect contract and shows declines without success',async()=>{
 confirmPayment.mockResolvedValue({error:{message:'Declined fixture'}});
 const success=jest.fn();
 render(<AIPaymentForm orderId={1} total={12} items={[]} clientSecret="fixture-not-real" onPaymentSuccess={success}/>);
 expect(screen.getByTestId('stripe-payment-element')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:/PAY/}));
 await waitFor(()=>expect(screen.getByText('Declined fixture')).toBeInTheDocument());
 expect(confirmPayment).toHaveBeenCalledWith({elements,redirect:'if_required'});
 expect(success).not.toHaveBeenCalled();
});
it('keeps assistant checkout client-secret guard',()=>{
 render(<AIPaymentForm orderId={1} total={12} items={[]} onPaymentSuccess={jest.fn()}/>);
 expect(screen.getByText('Missing Client Secret')).toBeInTheDocument();
 expect(confirmPayment).not.toHaveBeenCalled();
});
