# Cached behavior inference boundary

Retained behavior profile reads now require the current artifact ID, trained
source dimension, exact internal tensor length, finite bounded numeric entries,
nonzero vectors and a finite timestamp within the existing one-hour cache
lifetime. Invalid owner identities stop before the cache read. Cached corrupt,
old, foreign-artifact or dimension-shifted output cannot become a profile or
reranking input. Actual Redis tests preserve owner isolation and existing TTL.

This does not activate hidden behavior collection, infer new traits, replace a
learned model, train a model, migrate records or change consent vocabulary.
The learned checkpoint path and valid output contract remain unchanged. Broader
consent/lifecycle integration and live model quality remain separate acceptance.
