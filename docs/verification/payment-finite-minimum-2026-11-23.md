# Payment amount finite/minor-unit boundary

PaymentRequest explicitly rejects nonfinite Decimal amounts. Existing half-up two-decimal quantization remains, but amounts rounding to zero and amounts unrepresentable under Decimal precision produce validation errors before gateway execution, not zero-value requests or raw decimal failures.

Seven tests cover NaN/infinities, positive sub-cent rounded-zero values, extreme exponent and preserved0.005-to0.01 rounding. Full local migrated PostgreSQL19/Redis suite798 passed,4 skipped,20 existing warnings. No provider calls. This retains the application's existing two-decimal convention, not general currency minor-unit support or payment-provider minimum/maximum policy coverage.
