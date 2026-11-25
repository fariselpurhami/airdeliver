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
  // Unknown catalog image origins stay browser-direct, never a server-side
  // optimizer fetch. Same-origin and known reference hosts retain optimization.
  let directRemote = false;
  try {
    const url = new URL(source);
    directRemote = !['images.unsplash.com', 'ui-avatars.com'].includes(url.hostname) || url.protocol !== 'https:';
  } catch { /* Relative images use the existing local path. */ }
  const displayAlt = demo ? (demo.candidate && source !== '/images/demo-v1/neutral.svg' ? `${demo.candidate.title}. Demo reference, not the listed SKU variant.` : 'Demo illustration. Not a product photo.') : alt;
  return <Image {...props} src={source} alt={source === fallback ? `${displayAlt}. Image unavailable.` : displayAlt}
    unoptimized={!!demo || directRemote || source === fallback || props.unoptimized}
    onError={(event) => { if (source !== fallback) setFailedSource(input || null); onError?.(event); }} />;
}
