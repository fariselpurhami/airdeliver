'use client';

import React, {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Plus,
  Check,
  Rocket,
  TrendingUp,
  Bot,
  Star,
} from 'lucide-react';
import Image from 'next/image';
import { isDemoImageEligible } from '@/lib/catalog/demoImages';
import { CatalogImage } from './CatalogImage';
import { DemoImageAttribution } from './DemoImageAttribution';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';
import { CatalogPrice, listedCatalogPrice } from '../ai/CatalogPrice';
import { type Product } from './ProductCard';
import { api } from '@/lib/api';
import Link from 'next/link';
import { randomId } from '@/lib/random-id';

type ProductDetailsCardProduct = {
  sku?: string;
  attributes?: Record<string, unknown>;
  // Structural contract of only the fields this card renders. Accepts both
  // the full Product and the lighter AIProduct shape from the chat carousel.
  id: number | string;
  name: string;
  price?: number | string | null;
  price_status?: string;
  image_url?: string | null;
  description?: string;
  predicted_delivery?: string;
  trending_status?: string;
  stock_level?: string | null;
  currency?: string;
  rating?: number | null;
  inventory?: number;
  is_active?: boolean;
  isAIRec?: boolean;
};

type ProductDetailsCardProps = {
  product: ProductDetailsCardProduct;
  onClose: () => void;
};

const RATING_STARS = [0, 1, 2, 3, 4] as const;
const ADDED_STATE_DURATION_MS = 2000;
const DEFAULT_DESCRIPTION =
  'Specifications classified. High-performance unit ready for deployment.';

const LegacyProductDetailsCardComponent = ({
  product,
  onClose,
}: ProductDetailsCardProps) => {
  const addProductById = useAIOrderingStore((state) => state.addProductById);

  const [isAdded, setIsAdded] = useState(false);
  const addedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const uniqueBtnId = useMemo(
    () => `details-add-btn-${String(product.id)}`,
    [product.id]
  );


  const sku = useMemo(() => {
    const raw = typeof product.id === 'number' || typeof product.id === 'string'
      ? String(product.id)
      : '0';
    return raw.padStart(6, '0');
  }, [product.id]);

  const description = useMemo(
    () => product.description?.trim() || DEFAULT_DESCRIPTION,
    [product.description]
  );

  // No fabricated fallbacks: these blocks render only when the backend
  // supplies a real value. The old DEFAULT_DELIVERY/DEFAULT_TRENDING
  // constants showed invented data for every product.
  const predictedDelivery = useMemo(
    () => product.predicted_delivery?.trim() || null,
    [product.predicted_delivery]
  );

  const trendingStatus = useMemo(
    () => product.trending_status?.trim() || null,
    [product.trending_status]
  );

  const stockLevel = useMemo(() => {
    if (product.stock_level === null || product.stock_level === undefined || product.stock_level === '') {
      return null;
    }
    return String(product.stock_level);
  }, [product.stock_level]);

  const imageAlt = useMemo(
    () => product.name?.trim() || 'Product image',
    [product.name]
  );

  useEffect(() => {
    return () => {
      if (addedTimerRef.current) {
        clearTimeout(addedTimerRef.current);
      }
    };
  }, []);

  const handleAddToCart = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();

      addProductById({ ...product, id: product.id as number }, uniqueBtnId);
      setIsAdded(true);

      if (addedTimerRef.current) {
        clearTimeout(addedTimerRef.current);
      }

      addedTimerRef.current = setTimeout(() => {
        setIsAdded(false);
      }, ADDED_STATE_DURATION_MS);
    },
    [addProductById, product, uniqueBtnId]
  );

  const handleClose = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      onClose();
    },
    [onClose]
  );

  return (
    <motion.div
      role="dialog"
      aria-modal="true"
      aria-labelledby="product-details-title"
      initial={{ opacity: 0, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.985 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      className="w-full h-full max-w-[460px] max-h-[1050px] md:max-w-7xl md:h-[93vh] md:max-h-none overflow-hidden rounded-[73px] border border-white/10 bg-neutral-950 text-white shadow-2xl flex flex-col"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-10%] top-[-10%] h-40 w-40 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute bottom-[-12%] right-[-8%] h-52 w-52 rounded-full bg-fuchsia-500/10 blur-3xl" />
      </div>

      <button
        type="button"
        aria-label="Close product details"
        onClick={handleClose}
        className="absolute right-8 top-6 z-20 p-3 rounded-full border border-white/5 bg-black/40 text-gray-400 backdrop-blur-md transition-all duration-300 hover:bg-white/10 hover:text-white hover:border-white/20 active:scale-[0.98]"
      >
        <X className="h-5 w-5" />
      </button>
      <div className="relative flex flex-col flex-1 overflow-hidden">
        <section className="min-w-0 border-b border-white/10 shrink-0">
          <div className="relative h-[32dvh] max-h-[340px] min-h-[160px] w-full overflow-hidden bg-white/[0.03]">
            {product.image_url || isDemoImageEligible(product) ? (
              <CatalogImage product={product}
                src={product.image_url}
                alt={imageAlt}
                fill
                priority={false}
                sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 42vw"
                className="object-contain"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-white/[0.03]">
                <Rocket className="h-12 w-12 text-white/25" />
              </div>
            )}

            <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent p-4 sm:p-5">
              <div className="flex flex-wrap items-center gap-2 text-xs text-white/80 sm:text-sm">
                <span className="rounded-full border border-white/10 bg-black/35 px-3 py-1 backdrop-blur-md">
                  SKU: {sku}
                </span>
                {product.isAIRec ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-cyan-200 backdrop-blur-md">
                    <Bot className="h-3.5 w-3.5" />
                    AI Verified
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <DemoImageAttribution product={product} expanded />
        <section className="min-w-0">
          <div className="flex max-h-[calc(100dvh-12rem)] flex-col overflow-y-auto overscroll-contain px-4 py-4 sm:max-h-[calc(92dvh-2rem)] sm:px-6 sm:py-6">
            <div className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-2 text-amber-300">
                {RATING_STARS.map((star) => (
                  <Star key={star} className="h-4 w-4 fill-current" />
                ))}
                <span className="text-xs font-medium tracking-[0.18em] text-white/60 sm:text-sm">
                  (4.8/5.0 RATING)
                </span>
              </div>

              <h2
                id="product-details-title"
                className="min-w-0 break-words text-2xl font-semibold leading-tight tracking-tight sm:text-3xl [overflow-wrap:anywhere]"
              >
                {product.name}
              </h2>

              <div className="mt-4 flex flex-wrap items-end gap-x-3 gap-y-2">
                <div className="text-3xl font-bold leading-none text-white sm:text-4xl">
                  <CatalogPrice product={product} />
                </div>

                {stockLevel ? (
                  <div className="inline-flex items-center rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-200 sm:text-sm">
                    {stockLevel}
                  </div>
                ) : null}
              </div>

              <p className="mt-5 min-w-0 break-words text-sm leading-7 text-white/70 sm:text-base [overflow-wrap:anywhere]">
                {description}
              </p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4">
              {predictedDelivery && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 sm:p-4">
                  <div className="mb-2 flex items-center gap-2 text-cyan-300">
                    <Rocket className="h-4 w-4 shrink-0" />
                    <span className="text-xs uppercase tracking-[0.16em] text-white/55">
                      Delivery ETA
                    </span>
                  </div>
                  <div className="break-words text-sm font-medium text-white sm:text-base [overflow-wrap:anywhere]">
                    {predictedDelivery}
                  </div>
                </div>
              )}

              {trendingStatus && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 sm:p-4">
                  <div className="mb-2 flex items-center gap-2 text-fuchsia-300">
                    <TrendingUp className="h-4 w-4 shrink-0" />
                    <span className="text-xs uppercase tracking-[0.16em] text-white/55">
                      Demand
                    </span>
                  </div>
                  <div className="break-words text-sm font-medium text-white sm:text-base [overflow-wrap:anywhere]">
                    {trendingStatus}
                  </div>
                </div>
              )}

            </div>
          </div>
        </section>
      </div>
    </motion.div>
  );
};

// Original visual/source remains above; all live callers use the grounded view.
const ProductDetailsCardComponent = ({product,onClose}:ProductDetailsCardProps) => {

  const showAssistant=useAIOrderingStore(state=>state.setOverlayVisible);
  const send=useAIOrderingStore(state=>state.sendMessage);
  const assistantBusy=useAIOrderingStore(state=>state.isLoading);
  const [quantity,setQuantity]=useState(1);
  const [pending,setPending]=useState(false);
  const [notice,setNotice]=useState('');
  const [submitted,setSubmitted]=useState(false);
  const ref=useRef<HTMLDivElement>(null);
  const closeRef=useRef<HTMLButtonElement>(null);
  const busy=useRef(false);
  const mutationId=useRef<string | null>(null);
  const synthetic=Boolean(product.sku?.startsWith('ADL-DEV-v1-') || product.sku?.startsWith('ADL-DEMO-v1-') || ['airdeliver-dev-fixtures-v1','airdeliver-demo-v1'].includes(String(product.attributes?._seed_dataset)));
  const productId=typeof product.id==='number'?product.id:Number(product.id);
  const price=listedCatalogPrice(product);
  const available=!synthetic && product.is_active!==false && Number.isInteger(productId) && productId>0 && price!==null && !(typeof product.inventory==='number' && product.inventory<=0);
  const maxQuantity=typeof product.inventory==='number' && Number.isFinite(product.inventory)?Math.min(99,Math.max(1,Math.floor(product.inventory))):99;
  const description=synthetic?(product.description||'').replace(/Synthetic local test product, not a merchant offer\.?/gi,'').trim():(product.description||'').trim();
  const rating=!synthetic && typeof product.rating==='number' && Number.isFinite(product.rating) && product.rating>=0 && product.rating<=5?product.rating:null;
  const facts=Object.entries(product.attributes||{}).filter(([key,value])=>!key.startsWith('_') && typeof value==='string' && value.length<160).slice(0,6);
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null;
    closeRef.current?.focus();
    const onKey=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();event.stopImmediatePropagation();onClose();return;}
      if(event.key!=='Tab')return;
      const nodes=Array.from(ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),[tabindex="0"],summary')||[]).filter(node=>!node.closest('details:not([open])') || node.tagName==='SUMMARY');
      if(!nodes?.length)return;
      const first=nodes[0],last=nodes[nodes.length-1];
      if(event.shiftKey && document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first?.focus();}
    };
    document.addEventListener('keydown',onKey,true);
    return ()=>{document.removeEventListener('keydown',onKey,true);previous?.focus();};
  },[onClose]);
  const add=async()=>{
    if(busy.current || !available || submitted)return;
    busy.current=true;setPending(true);setNotice('');
    try {
      mutationId.current ??= randomId();
      const response=await api.post('/ai-ordering/cart/add',{product_id:productId,quantity},{headers:{'Idempotency-Key':mutationId.current}});
      const accepted=response.status>=200 && response.status<300;
      setSubmitted(true);
      setNotice(accepted?'Request sent. Check your cart for confirmation before checkout.':'Cart update could not be confirmed. Check your cart before trying again.');
    } catch {setSubmitted(true);setNotice('Cart update could not be confirmed. Check your cart before trying again.');}
    finally{busy.current=false;setPending(false);}
  };
  return <motion.div ref={ref} role="dialog" aria-modal="true" aria-labelledby="product-details-title" initial={{opacity:0,y:12,scale:.99}} animate={{opacity:1,y:0,scale:1}} exit={{opacity:0,y:8}} transition={{duration:.2}}
    className="relative isolate flex outline-none max-h-[calc(100dvh-3rem)] w-full max-w-[460px] flex-col overflow-hidden rounded-[30px] bg-[#08090a]/95 text-white shadow-[0_30px_120px_rgba(0,0,0,.65)] backdrop-blur-3xl md:max-w-[1040px] md:flex-row md:rounded-[38px]" style={{fontFamily:"-apple-system, BlinkMacSystemFont, 'Inter', sans-serif"}}>
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10" style={{backgroundImage:'radial-gradient(ellipse at 80% 5%,rgba(255,255,255,.055),transparent 60%),radial-gradient(1px 1px at 20% 65%,rgba(255,255,255,.15),transparent),radial-gradient(1px 1px at 75% 88%,rgba(255,255,255,.1),transparent)'}}/>
    <div className="relative flex shrink-0 items-center justify-between px-5 py-3 md:absolute md:inset-x-0 md:top-0 md:z-20 md:px-6 md:py-4">
      <span className="text-xs font-medium text-white/45 md:rounded-full md:bg-black/35 md:px-3 md:py-2 md:backdrop-blur-xl">Product details</span>
      <button ref={closeRef} type="button" aria-label="Close product details" onClick={onClose} className="flex h-11 w-11 items-center justify-center rounded-full bg-white/[.06] text-white/70 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-white"><X size={20}/></button>
    </div>
    <div className="min-h-0 overflow-y-auto overscroll-contain md:grid md:w-full md:grid-cols-[1.05fr_1fr]">
      <section aria-label="Product image" className="relative aspect-[6/5] w-full overflow-hidden bg-[#f1f0eb] md:sticky md:top-0 md:aspect-auto md:min-h-[620px]">
        {product.image_url || isDemoImageEligible(product)?<CatalogImage product={product} src={product.image_url} alt={product.name} fill sizes="(max-width:768px) 94vw, 540px" className="object-contain"/>:<div className="flex h-full items-center justify-center text-sm text-black/45">Image unavailable</div>}
      </section>
      <section className="min-w-0 px-6 pb-6 pt-6 md:px-9 md:pb-9 md:pt-24">
        {rating!==null && <p className="mb-3 flex items-center gap-2 text-sm text-white/55"><Star size={14} className="fill-amber-200 text-amber-200" aria-hidden="true"/>{rating.toFixed(1)} <span className="text-white/35">Catalog rating</span></p>}
        <h2 id="product-details-title" className="break-words text-[26px] font-medium leading-[1.18] tracking-[-.035em] md:text-[34px]">{product.name}</h2>
        <div className="mt-4 text-[30px] font-medium leading-none tracking-[-.035em] md:text-[34px]"><CatalogPrice product={product}/></div>
        <p className="mt-6 text-sm leading-[1.8] text-white/55 md:text-[15px]">{description||'Product details are not available yet.'}</p>
        {facts.length>0 && <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-4">{facts.map(([key,value])=><div key={key}><dt className="text-xs text-white/35">{key.replaceAll('_',' ')}</dt><dd className="mt-1 break-words text-sm text-white/75">{String(value)}</dd></div>)}</dl>}
        <DemoImageAttribution product={product} borderless/>
        {(product.predicted_delivery || product.stock_level || product.trending_status) && <div className="mt-5 flex flex-wrap gap-2 text-xs text-white/55">{[product.predicted_delivery,product.stock_level,product.trending_status].filter(Boolean).map((fact,index)=><span key={index} className="rounded-full bg-white/[.055] px-3 py-2">{fact}</span>)}</div>}
        <div className="mt-7 space-y-3">
          <div className="flex items-center justify-between"><label htmlFor="product-quantity" className="text-sm text-white/50">Quantity</label><div className="flex items-center rounded-full bg-white/[.055] p-1"><button type="button" aria-label="Decrease quantity" disabled={!available || pending || submitted || quantity<=1} onClick={()=>setQuantity(n=>n-1)} className="h-10 w-10 rounded-full text-lg disabled:opacity-25">−</button><input id="product-quantity" aria-label="Quantity" readOnly value={quantity} className="w-9 bg-transparent text-center text-sm outline-none"/><button type="button" aria-label="Increase quantity" disabled={!available || pending || submitted || quantity>=maxQuantity} onClick={()=>setQuantity(n=>n+1)} className="h-10 w-10 rounded-full text-lg disabled:opacity-25">+</button></div></div>
          <button type="button" disabled={!available || pending || submitted} onClick={()=>void add()} className="min-h-12 w-full rounded-full bg-white px-5 py-3.5 text-sm font-semibold text-black transition hover:bg-white/85 disabled:bg-white/10 disabled:text-white/35">{pending?'Sending cart request...':submitted?'Check cart for confirmation':available?'Add to cart':'Unavailable to purchase'}</button>
          {notice && <p role="status" className="text-xs leading-relaxed text-white/60">{notice}</p>}
          <div className="grid grid-cols-2 gap-2"><Link href="/cart" className="flex min-h-12 items-center justify-center rounded-full bg-white/[.055] px-3 text-sm text-white/70 transition hover:bg-white/10">View cart</Link><button type="button" disabled={assistantBusy} onClick={()=>{if(assistantBusy)return;showAssistant(true);send('Tell me about '+product.name);onClose();}} className="min-h-12 rounded-full bg-white/[.055] px-3 text-sm text-white/70 transition hover:bg-white/10 disabled:opacity-40">Ask about this</button></div>
        </div>
      </section>
    </div>
  </motion.div>;
};

export const ProductDetailsCard = memo((props: ProductDetailsCardProps) => <ProductDetailsCardComponent key={String(props.product.id)} {...props}/>);
ProductDetailsCard.displayName = 'ProductDetailsCard';
