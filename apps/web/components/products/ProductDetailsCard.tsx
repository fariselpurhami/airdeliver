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
import { CatalogPrice } from '../ai/CatalogPrice';
import { type Product } from './ProductCard';

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

const ProductDetailsCardComponent = ({
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

        <DemoImageAttribution product={product} />
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

export const ProductDetailsCard = memo(ProductDetailsCardComponent);
ProductDetailsCard.displayName = 'ProductDetailsCard';
