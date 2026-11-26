# AI accuracy evaluation (English), v1 seed

Status: seed only. 24 cases cannot give a tight accuracy number (a perfect score on 24 still has a 95% lower bound near 86%). Target is 200+ cases before any headline percentage is quoted.

Method: each case has rule-based pass criteria (required pattern, forbidden patterns, length, question count, whether products may be returned). No model judges the model. score.py reports per-category and overall pass rate with a Wilson 95% interval and n, and counts unscored cases.

Not yet built: the runner that sends each case through the real service with the free-tier provider, within the user's free-tier grant, recording responses to a ledger. Cases here are development material; freeze a held-out split by hash before reporting a final number.
Old 4-case Groq experiment results are historical and are not part of these numbers.
