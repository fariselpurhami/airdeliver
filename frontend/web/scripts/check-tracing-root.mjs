import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const source=await fs.readFile(new URL('../next.config.mjs',import.meta.url),'utf8');
async function fixture(kind){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'adl-tracing-'));
 const app=kind!=='standalone'?path.join(root,'frontend','web'):path.join(root,'app');
 await fs.mkdir(app,{recursive:true});
 if(kind!=='standalone')await fs.writeFile(path.join(root,'pnpm-workspace.yaml'),'packages: []\n');
 if(kind==='container')await fs.mkdir(path.join(root,'node_modules','.pnpm'),{recursive:true});
 const config=path.join(app,'next.config.mjs');await fs.writeFile(config,source);
 try{
  const {default:c}=await import(pathToFileURL(config));
  assert.equal(c.outputFileTracingRoot,c.turbopack.root);
  assert.equal(c.turbopack.root,kind==='standalone'?app:root);
 }finally{await fs.rm(root,{recursive:true,force:true});}
}
for(const kind of ['workspace','container','standalone'])test(kind+' tracing and Turbopack share the actual dependency root',()=>fixture(kind));
