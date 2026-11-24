# Trending dialog chrome isolation

The earlier shell-owned ordering fix hid/inerted site chrome for ordering only.
Explore uses the separate UI product-overlay flag. Its product dialog also sat
inside the transformed, isolated home subtree, below the fixed site header.

AppShell now hides/inerts header, footer and chatbot for either overlay flag.
ProductOverlay uses a body portal outside the inert/transformed home, preserving
product fetch/normalization/cards and all Explore handlers. Its dialog and close
control have accessible names and mobile safe-area padding. Both responsive home
hero definitions use the same Explore handler and dialog; no second product
modal entrypoint was found. Standalone products-page header remains unchanged.

178 frontend tests pass with coverage disabled (same test scope as frontend CI),
TypeScript noEmit passes. New real-store integration clicks Explore, checks body
portal outside inert main and hidden header, then close restores shell chrome.
Rendered actual component markup/styles at390x844 and393x852 with simulated
59px top/34px bottom safe areas: no visible site header, close control clear of
safe areas, no horizontal overflow. Safe-area inset emulation is not a real
Safari/device receipt. No backend/provider work or owner deployment performed.
