# Stripe browser SDK major refresh

Update React Stripe6.11 to7.1 and Stripe.js9.17 to10.3 together. Registry peer contract requires Stripe.js>=10.3 <11 and supports current React19.3.1. Reviewed official releases: removed PaymentRequestButton and Elements paymentMethodTypes are not used anywhere in this app. Current Elements/PaymentElement/useStripe/useElements/confirmPayment paths typecheck without application behavior edits.

Root and genuinely isolated standalone context: actual-script frozen pnpm12.6 installs,111tests/20suites, TypeScript and production builds pass. Added tests for standard checkout confirmPayment return URL, assistant if_required confirmation, declined result not claiming success, and missing-secret guard. Tests mock SDK calls only, no payment/provider action. Neither production forms nor provider code altered. Root audit reports zero matched advisories, not a vulnerability-free guarantee.

Not proven: real Stripe network/iframe rendering and test-mode payment lifecycle. No key or payment authorization used. Do not call this live payment certification. Stripe.js10 selects Endive runtime, so provider end-to-end validation is still required before production rollout. Server-side API version unchanged.

Sources: https://github.com/stripe/react-stripe-js/releases , https://github.com/stripe/stripe-js/releases , https://docs.stripe.com/sdks/stripejs-versioning , https://registry.npmjs.org/%40stripe%2Freact-stripe-js/latest , https://registry.npmjs.org/%40stripe%2Fstripe-js/latest .
