import {render,screen} from '@testing-library/react';
import {parseSupportReply} from '@/lib/support-catalog-reply';
import {CatalogEvidence} from '@/components/ai/CatalogEvidence';
import {CatalogPrice} from '@/components/ai/CatalogPrice';
import {useAIOrderingStore} from '@/hooks/useAIOrderingStore';
const card={id:1,name:'Studio Headphones',price:'19.99',currency:'USD',price_status:'listed',evidence_kind:'seeded_demo',stock_status:'demo',availability_note:'Demo catalog. Price and stock are synthetic, not a merchant offer.'};
it('keeps evidence and cards with the model text across the actual HTTP store boundary',async()=>{
  const snapshot=useAIOrderingStore.getState();
  const fetchBefore=global.fetch;
  global.fetch=jest.fn<typeof fetch>().mockResolvedValue({ok:true,json:async()=>({text:'Compare the catalog option below.',products:[card],response_kind:'catalog_results'})} as Response);
  try {
    useAIOrderingStore.setState({messages:[],ackTimeouts:{}});
    await useAIOrderingStore.getState()._postSupportChat('headphones',null);
    expect(useAIOrderingStore.getState().messages[0]).toMatchObject({contentType:'product_carousel',products:[card],content:'Compare the catalog option below.'});
  } finally {useAIOrderingStore.setState(snapshot,true);global.fetch=fetchBefore;}
});
it.each([{...card,price:'NaN'},{...card,evidence_kind:undefined},{...card,stock_status:'verified'},{...card,currency:undefined}])('rejects malformed cards instead of displaying unaccompanied sales text',bad=>{
  expect(()=>parseSupportReply({text:'Product',products:[bad]})).toThrow();
});
it('shows demo source and non-USD amounts without a dollar sign',()=>{
  render(<><CatalogEvidence product={card}/><CatalogPrice product={{price:'19.99',currency:'EUR',price_status:'listed'}}/></>);
  expect(screen.getByText('Demo catalog')).toBeInTheDocument();
  expect(screen.getByText(/synthetic, not a merchant offer/)).toBeInTheDocument();
  expect(screen.getByText('EUR 19.99')).toBeInTheDocument();
});
