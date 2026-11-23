# Air Assistant visual refresh

Restyle Chatbot.tsx only: navy glass panel, rounded32/40px shell, cyan edge accents, restrained user/assistant bubbles, clear Air Assistant title, capsule composer and white send affordance. Mobile uses dynamic viewport height and safe-area footer, desktop540px bounded panel. Hide the duplicate floating launcher while the panel is open so it cannot cover the mobile composer; header close remains. Add labels to existing controls.

No session, send, action-option, store, greeting, API or provider changes. Existing explainability, typing and body scroll lock kept. Added UI contract test for identity, send and close wiring. Local108 tests/20 suites, TypeScript and production build pass. Actual production preview at390px and desktop inspected after fixing a discovered duplicate-close overlap. Greeting fixture fully intercepted, no Groq/provider/backend request. No owner-machine action. CI must pass before merge review.
