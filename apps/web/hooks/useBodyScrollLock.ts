
import { useLayoutEffect } from 'react';

type UseBodyScrollLockOptions = {
  locked: boolean;
  lockTarget?: HTMLElement | null;
};

const BODY_SCROLL_LOCK_ATTR = 'data-body-scroll-lock';
const BODY_SCROLL_LOCK_Y_ATTR = 'data-body-scroll-y';
const BODY_SCROLL_LOCK_COUNT_ATTR = 'data-body-scroll-lock-count';

function getBody(): HTMLBodyElement | null {
  if (typeof document === 'undefined') return null;
  return document.body;
}

export function useBodyScrollLock({
  locked,
  lockTarget,
}: UseBodyScrollLockOptions): void {
  useLayoutEffect(() => {
    const body = getBody();
    if (!locked || !body) return;

    const target = lockTarget ?? body;
    const activeLocks = Number(body.getAttribute(BODY_SCROLL_LOCK_COUNT_ATTR) ?? '0');

    if (activeLocks === 0) {
      const scrollY = window.scrollY;
      const previous = {
        overflow: body.style.overflow,
        position: body.style.position,
        top: body.style.top,
        width: body.style.width,
        left: body.style.left,
        right: body.style.right,
      };

      body.setAttribute(
        BODY_SCROLL_LOCK_ATTR,
        JSON.stringify(previous),
      );
      body.setAttribute(BODY_SCROLL_LOCK_Y_ATTR, String(scrollY));

      body.style.overflow = 'hidden';
      body.style.position = 'fixed';
      body.style.top = `-${scrollY}px`;
      body.style.width = '100%';
      body.style.left = '0';
      body.style.right = '0';
    }

    body.setAttribute(BODY_SCROLL_LOCK_COUNT_ATTR, String(activeLocks + 1));

    return () => {
      const latestBody = getBody();
      if (!latestBody) return;

      const currentLocks = Number(
        latestBody.getAttribute(BODY_SCROLL_LOCK_COUNT_ATTR) ?? '0',
      );
      const nextLocks = Math.max(0, currentLocks - 1);

      if (nextLocks > 0) {
        latestBody.setAttribute(BODY_SCROLL_LOCK_COUNT_ATTR, String(nextLocks));
        return;
      }

      latestBody.removeAttribute(BODY_SCROLL_LOCK_COUNT_ATTR);

      const savedStylesRaw = latestBody.getAttribute(BODY_SCROLL_LOCK_ATTR);
      const savedScrollY = latestBody.getAttribute(BODY_SCROLL_LOCK_Y_ATTR);

      let savedStyles: Partial<CSSStyleDeclaration> = {};

      if (savedStylesRaw) {
        try {
          savedStyles = JSON.parse(savedStylesRaw) as Partial<CSSStyleDeclaration>;
        } catch {
          savedStyles = {};
        }
      }

      latestBody.style.overflow = savedStyles.overflow ?? '';
      latestBody.style.position = savedStyles.position ?? '';
      latestBody.style.top = savedStyles.top ?? '';
      latestBody.style.width = savedStyles.width ?? '';
      latestBody.style.left = savedStyles.left ?? '';
      latestBody.style.right = savedStyles.right ?? '';

      latestBody.removeAttribute(BODY_SCROLL_LOCK_ATTR);
      latestBody.removeAttribute(BODY_SCROLL_LOCK_Y_ATTR);

      if (savedScrollY) {
        window.scrollTo({
          top: Number(savedScrollY) || 0,
          left: 0,
          behavior: 'auto',
        });
      }
    };
  }, [locked, lockTarget]);
}
