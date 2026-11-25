import React from 'react';
import { test, expect, jest } from '@jest/globals';
import { render, screen, fireEvent } from '@testing-library/react';
import Panel, { PaymentMetrics, formatRecordedAmount } from '@/components/admin/PaymentMetricsPanel';
const data:PaymentMetrics={generated_at:new Date().toISOString(),from_at:'2026-11-24T12:00:00Z',to_at:'2026-11-25T12:00:00Z',timezone:'UTC',definition:'recorded_paid_order_gross',complete:true,currencies:[{currency:'USD',amount:'15.10',order_count:151,buckets:[]},{currency:'EUR',amount:'0.20',order_count:1,buckets:[]}],paid_without_timestamp:2,paid_invalid_amount_or_currency:1};
const props={loading:false,error:false,range:'24H' as const,onRange:jest.fn(),onRetry:jest.fn()};
test('currencies stay separate, scope/exclusions visible, no fake revenue/online claim',()=>{
 render(<Panel {...props} data={data}/>);
 expect(screen.getByText('USD 15.10')).toBeInTheDocument();expect(screen.getByText('EUR 0.20')).toBeInTheDocument();
 expect(screen.getByText(/Not settled funds/)).toBeInTheDocument();expect(screen.getByText(/2 paid records without/)).toBeInTheDocument();
 expect(screen.queryByText('ONLINE')).not.toBeInTheDocument();expect(props.onRange).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'7D'}));expect(props.onRange).toHaveBeenCalledWith('7D');
});
test('error retains stale data with explicit warning and user retry only',()=>{
 render(<Panel {...props} error data={data}/>);expect(props.onRetry).not.toHaveBeenCalled();
 expect(screen.getByRole('alert')).toHaveTextContent(/couldn't be refreshed/);expect(screen.getByText(/Snapshot may be out of date/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Try again'}));expect(props.onRetry).toHaveBeenCalledTimes(1);
});
test('empty is not proof of no payments, invalid timestamps do not crash',()=>{
 const {rerender}=render(<Panel {...props} data={{...data,currencies:[]}}/>);
 expect(screen.getByText(/does not prove no payments/)).toBeInTheDocument();
 rerender(<Panel {...props} data={{...data,from_at:'invalid'}}/>);expect(screen.getByRole('alert')).toBeInTheDocument();
});
test('never guesses currency or displays nonfinite amount',()=>{
 expect(formatRecordedAmount(10,'EUR')).toBe('EUR 10.00');expect(formatRecordedAmount('NaN','USD')).toBe('Amount unavailable');expect(formatRecordedAmount(10,'???')).toBe('Amount unavailable');
});

test('failed refresh never presents an empty previous snapshot as current',()=>{
 render(<Panel {...props} error data={{...data,currencies:[]}}/>);
 expect(screen.getByText(/last successful snapshot had no timestamped/)).toBeInTheDocument();
 expect(screen.queryByText(/^No timestamped paid orders in this window/)).not.toBeInTheDocument();
});
