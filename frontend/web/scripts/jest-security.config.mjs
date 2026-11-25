import base from '../jest.config.mjs';
export default async function securityConfig() {
 const config=typeof base==='function'?await base():await base;
 return {...config,rootDir:process.cwd(),testPathIgnorePatterns:['/node_modules/','/.next/'],setupFilesAfterEnv:[],testEnvironment:'node',collectCoverage:false,testMatch:['**/__tests__/ProxySecurity.test.ts']};
}
