# Mobile catalog hero

- Mobile catalog uses the original home eight-card positions, sizes, images and motion, below the existing 1024px mobile breakpoint.
- Desktop retains the same six-card renderer and stage dimensions.
- Home implementation and mobile install gate are unchanged. Mobile `/products` remains subject to the existing standalone/PWA route policy.
- Local fixture browser: 390px standalone showed 8 mobile cards, 0 desktop cards, no horizontal overflow. 1440px showed 0 mobile cards, 6 desktop cards, no horizontal overflow. Actual pixels inspected at both sizes.
- Local frontend: 99 tests passed, TypeScript and production build passed. No real API/provider call or database write. Backend code unchanged.
