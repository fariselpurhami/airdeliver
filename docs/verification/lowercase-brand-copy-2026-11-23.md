# Lowercase brand copy audit

Application presentation spelling is `airdeliver`. The existing product label `airdeliverOS Insight` is preserved.

Audited tracked frontend app/components/hooks/lib/public source and backend application source for mixed/uppercase brand mentions, including page metadata, alt text, notification copy, errors, prompts and fallbacks. Corrected welcome text, logo alt text, first-purchase badge description, model persona prompts and the overlay fallback brand. The fallback brand opts out of CSS uppercase so its lowercase spelling survives rendering. Merchant brand capitalization is unchanged.

Technical identifiers, environment variables, package names, URLs, repository names, archived bytecode, documentation headings and license text are not renamed. The sanitizer's two legacy input spellings remain intentional. This is an authored-source audit, not a claim that external catalog data, old persisted notifications or arbitrary model output have been rewritten.

Regression guards scan authored frontend source and backend Python string literals. Backend comments and the sanitizer's legacy input literals are excluded. Local full verification: 1004 backend tests passed, 4 skipped; 95 frontend tests passed; TypeScript and Next production build passed. No model/provider request, database mutation or deployment.
