# Shared hero floating cards

Home desktop, home mobile install view and catalog now render the same six cards in one shared stage. Home retains its own headline and order/explore controls; mobile retains its install headline and download control. Existing routes and PWA redirect policy are unchanged.

Desktop uses the catalog card dimensions and positions. Both routes use a 48%-width protected center. Catalog headline font size is bounded to that center rather than overflowing into cards. Mobile/tablet uses complete cards in two rows with a clear central text/control area, replacing prior negative edge offsets and clipping. A 1000px mobile stage fits the longer catalog and install copy without overlaps. Decorative cards do not capture input and respect reduced motion for floating animation. Legacy home card code/config remains available but is no longer rendered.

Real Chromium route captures at 1440x1000 and 390x844 inspected for home and catalog. Mobile catalog and normal home were also checked in standalone/PWA mode; ordinary mobile catalog redirects home by existing PWAGuard. Fixed an existing mobile global hide rule that matched bottom-position utility classes and hid decorative cards, excluding only this shared card subtree. No authentication bypass, provider call or backend connection was used. Test API responses were intercepted as empty inventory, so catalog product inventory is not validated by these captures. Remote decorative stock images are unchanged and not certified model/variant photos.

Frontend: 96 tests passed, TypeScript passed, production build passed. Brand main post-merge backend/FE/guard passed separately. No API business logic, migration or seed changes in this PR.
