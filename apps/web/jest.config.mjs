// file: apps/web/jest.config.mjs
// version: 1.0.0
// date: 2025-09-23
// author: Gemini

import nextJest from 'next/jest.js'
 
const createJestConfig = nextJest({
  dir: './',
})
 
/** @type {import('jest').Config} */
const config = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
}
 
export default createJestConfig(config)
