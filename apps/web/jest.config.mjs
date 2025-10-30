// apps/web/jest.config.mjs

import nextJest from 'next/jest.js'
import { pathsToModuleNameMapper } from 'ts-jest'
import { readFileSync } from 'fs'

const tsconfig = JSON.parse(readFileSync('./tsconfig.json', 'utf8'))

const createJestConfig = nextJest({
  dir: './',
})

const config = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: pathsToModuleNameMapper(tsconfig.compilerOptions.paths, {
    prefix: '<rootDir>/',
  }),
}
 
export default createJestConfig(config)
