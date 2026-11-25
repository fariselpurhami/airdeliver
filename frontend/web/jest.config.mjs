/** frontend/web/jest.config.mjs **/

import nextJest from 'next/jest.js';
import { readFileSync } from 'fs';
import { pathsToModuleNameMapper } from 'ts-jest';

// tsconfig.json carries a leading comment banner; strip comments before parsing.
const tsconfig = JSON.parse(
  readFileSync('./tsconfig.json', 'utf8').replace(/^\s*\/\*[\s\S]*?\*\//, '')
);

const createJestConfig = nextJest({
  dir: './',
});

const config = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  // next-auth v5 ships ESM only; let the next/jest transform compile it.
  transformIgnorePatterns: ['/node_modules/(?![^]*next-auth/)'],
  moduleNameMapper: pathsToModuleNameMapper(tsconfig.compilerOptions.paths, {
    prefix: '<rootDir>/',
  }),
  collectCoverage: true,
  collectCoverageFrom: [
    'src/app/**/*.{js,jsx,ts,tsx}',
    'src/components/**/*.{js,jsx,ts,tsx}',
    'src/lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50,
    },
  },
};

export default createJestConfig(config);
