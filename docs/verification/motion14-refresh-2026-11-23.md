# Motion14 dependency refresh

Upgrade framer-motion13.5.1 to14.14.0 and matching locked internals in both contexts. Official upgrade guide reports no public React breaking changes in14, internal APIs deprecated and internal package versions tied more strictly. No application logic edits.

Root and genuine isolated standalone: pnpm12.6 actual-script frozen installs,109tests/20suites, TypeScript and production builds pass. Production-preview Air Assistant390px/desktop initial and conversation state inspected with intercepted API fixtures, no backend/provider request. Audit reports zero matched advisories, not a guarantee. Motion/reduced-motion close/send tested in existing suite. Visual screenshots are static verification, not proof of every interaction across every browser.

Sources: https://motion.dev/docs/react-upgrade-guide , https://raw.githubusercontent.com/framer/motion/main/CHANGELOG.md , https://registry.npmjs.org/framer-motion/latest .
