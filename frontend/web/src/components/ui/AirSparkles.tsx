import type { SVGProps } from 'react';

/** Shopping entry mark: one large four-point star and two smaller stars. */
export function AirSparkles(props: SVGProps<SVGSVGElement>) {
  return <svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true" {...props}>
    <path d="M13 6.5C12 14.5 9 17.5 1 18.5c8 1 11 4 12 12 1-8 4-11 12-12-8-1-11-4-12-12Z" />
    <path d="M24 0c-.5 5-2.5 7-7.5 7.5C21.5 8 23.5 10 24 15c.5-5 2.5-7 7.5-7.5C26.5 7 24.5 5 24 0Z" />
    <path d="M27 21c-.3 3.3-1.7 4.7-5 5 3.3.3 4.7 1.7 5 5 .3-3.3 1.7-4.7 5-5-3.3-.3-4.7-1.7-5-5Z" />
  </svg>;
}
