# Unique PayPal capture identities before funds aggregation

Completed-funds verification now requires each capture ID be a nonempty unique string. It cannot count the same capture twice to reach the expected paid total. Multiple distinct completed captures with the exact expected aggregate remain supported. Existing order/owner/currency/completion checks unchanged.

Two controlled provider-body tests cover duplicate-ID double counting and valid distinct split captures. Full disposable PostgreSQL19/Redis local suite801 passed,4 skipped,20 existing warnings. No PayPal requests. This is response-contract hardening, not a claim about PayPal emitting duplicate records or a live financial audit.
