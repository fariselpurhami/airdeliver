'use client';
import Image from 'next/image';
import { demoImagePresentation, type DemoIdentity } from '@/lib/catalog/demoImages';
import { useState, type ComponentProps } from 'react';

const fallback = '/images/catalog-placeholder.svg';
type Props = Omit<ComponentProps<typeof Image>, 'src'> & { src?: string | null; product?: DemoIdentity };

export function CatalogImage({ src, alt, onError, product, ...props }: Props) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const demo = demoImagePresentation(product);
  const input = demo?.asset ?? src;
  const source = input && input !== failedSource ? input : (demo ? '/images/demo-v1/neutral.svg' : fallback);
  const displayAlt = demo ? (demo.candidate && source !== '/images/demo-v1/neutral.svg' ? `${demo.candidate.title}. Demo reference, not the listed SKU variant.` : 'Demo illustration. Not a product photo.') : alt;
  return <Image {...props} src={source} alt={source === fallback ? `${displayAlt}. Image unavailable.` : displayAlt}
    unoptimized={!!demo || source === fallback || props.unoptimized}
    onError={(event) => { if (source !== fallback) setFailedSource(input || null); onError?.(event); }} />;
}
