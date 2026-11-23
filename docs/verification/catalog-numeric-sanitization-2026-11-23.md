# Finite catalog numbers at model/ranking boundary

Existing numeric sanitizers now catch integer overflow and replace NaN/infinite floats with the existing fallback rather than sending invalid JSON numeric tokens or destabilizing ranking. No change to normal finite catalog values.

Four cases verify finite JSON-safe price/rating and safe invalid-ID fallback. Full local migrated PostgreSQL19/Redis suite808 passed,4 skipped,20 existing warnings. This preserves existing zero fallback semantics; zero must not be interpreted as proof that an unknown-priced item is free. Current catalog verification at checkout remains separate. No provider calls or broad model factuality claim.
