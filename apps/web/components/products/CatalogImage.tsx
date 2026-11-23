'use client';
import Image from 'next/image';
import { useState, type ComponentProps } from 'react';

const fallback = '/images/catalog-placeholder.svg';
type Props = Omit<ComponentProps<typeof Image>, 'src'> & { src?: string | null };

export function CatalogImage({ src, alt, onError, ...props }: Props) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const source = src && src !== failedSource ? src : fallback;
  return <Image {...props} src={source} alt={source === fallback ? `${alt}. Image unavailable.` : alt}
    unoptimized={source === fallback || props.unoptimized}
    onError={(event) => { if (source !== fallback) setFailedSource(src || null); onError?.(event); }} />;
}
