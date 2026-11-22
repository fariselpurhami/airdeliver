// Shared typing for jest-injected globals (see jest.setup.js). The values
// stay as runtime globals so the SWC jest transform keeps hoisting
// jest.mock() calls; this declaration file supplies their types.
import type * as JestGlobals from '@jest/globals';

declare global {
  const jest: typeof JestGlobals.jest;
  const describe: typeof JestGlobals.describe;
  const it: typeof JestGlobals.it;
  const expect: typeof JestGlobals.expect;
  const beforeEach: typeof JestGlobals.beforeEach;
  const afterEach: typeof JestGlobals.afterEach;
}

export {};
