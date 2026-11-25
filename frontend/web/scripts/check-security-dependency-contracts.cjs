// Guard the exact APIs used by the scoped advisory overrides.
const assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const path=require('node:path');
const fs=require('node:fs');
function packageEntry(name){
 try{return require.resolve(name);}catch{}
 for(const root of [path.join(process.cwd(),'node_modules','.pnpm'),path.resolve(process.cwd(),'../..','node_modules','.pnpm')]){
  if(!fs.existsSync(root))continue;
  for(const dir of fs.readdirSync(root).filter(p=>p.startsWith(name.replace('/','+')+'@'))){
   const candidate=path.join(root,dir,'node_modules',name);
   if(fs.existsSync(candidate))return require.resolve(candidate);
  }
 }
 throw Error('Missing test dependency '+name);
}
function dependency(parent,name){return createRequire(packageEntry(parent))(name);}
const typographyRequire=createRequire(require.resolve('@tailwindcss/typography'));
const parser=typographyRequire('postcss-selector-parser');
assert.equal(parser().astSync('article > :where(h1,h2):not(.skip)').toString(),'article > :where(h1,h2):not(.skip)');
const fixture=path.join(__dirname,'..','__tests__');
for(const parent of ['jest-runtime','jest-config','@jest/reporters','test-exclude']){
 const {glob}=dependency(parent,'glob');
 assert.equal(typeof glob.sync,'function');
 assert.ok(glob.sync('*.test.ts*',{cwd:fixture,nodir:true}).length>10,parent);
}
const {minimatch}=dependency('test-exclude','minimatch');
assert.equal(minimatch('components/Card.tsx','**/*.tsx',{dot:true}),true);
const TestExclude=require(packageEntry('test-exclude'));const exclude=new TestExclude({cwd:path.join(__dirname,'..'),include:['src/components/**/*.tsx'],exclude:['**/node_modules/**']});
assert.equal(exclude.shouldInstrument(path.join(__dirname,'..','src','components','products','ProductCard.tsx')),true);
assert.ok(exclude.globSync().some(p=>p.includes('ProductCard.tsx')));
exclude.glob().then(files=>{assert.ok(files.some(p=>p.includes('ProductCard.tsx')));console.log('Scoped dependency API contracts passed');}).catch(error=>{console.error(error);process.exitCode=1;});
