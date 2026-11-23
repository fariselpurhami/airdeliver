# Home viewport/background fix

Cause: new desktop stage stopped at 85vh/820px on a taller viewport. The next HowItWorks section began with 128/192px padding on a flat background, making an empty dark strip. Not missing data or a failed provider.

Home desktop now has a home-only minimum of max(820px,100dvh), with 100svh fallback. Catalog stage is unchanged. Existing following sections get a lightweight continuous CSS atmosphere through their padding, and HowItWorks top padding is reduced to 48/64px. No section/content/route removed. Mobile original eight-card positions remain untouched; mobile install hero also covers 100dvh. No provider/API/database call.

Verified real Chromium desktop1440x1000 and mobile390x844 in PWA and install-browser modes, plus screenshots extending beyond hero boundary. Desktop first viewport now fully starry; mobile next-section padding no longer flat black, install view no premature footer/remainder in viewport. Initial implementation still had large sparse nextsection space, reduced its top padding and re-rendered. Frontend98tests, TypeScript and productionbuild passed. Owner-host verification still follows merge.
