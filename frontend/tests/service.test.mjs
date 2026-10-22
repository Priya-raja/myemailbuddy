import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
const source=readFileSync(new URL('../lib/service.ts',import.meta.url),'utf8');
function service(fetch){
 const exports={};
 const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 vm.runInNewContext(js,{exports,process:{env:{NEXT_PUBLIC_API_BASE_URL:'https://api.example.test/'}},fetch,AbortSignal,Date,Promise,Error,setTimeout:callback=>{callback();return 0;}});
 return exports;
}
test('first connection checks health and caches readiness without calling a model route',async()=>{
 const urls=[],states=[];
 const api=service(async url=>{urls.push(url);return new Response('{"status":"ok"}');});
 await api.ensureServiceReady(value=>states.push(value));await api.ensureServiceReady();
 assert.deepEqual(urls,['https://api.example.test/health']);assert.deepEqual(states,[true,false]);
});
test('cold-start health failure is retried before any writing request',async()=>{
 let calls=0;
 const api=service(async url=>{assert.match(url,/\/health$/);calls++;return calls===1?new Response('Waking up',{status:503}):new Response('{"status":"ok"}');});
 await api.ensureServiceReady();assert.equal(calls,2);
});
test('missing pilot configuration fails promptly rather than looping',async()=>{
 let calls=0;const states=[];
 const api=service(async()=>{calls++;return new Response('{"status":"not_ready"}',{status:503});});
 await assert.rejects(api.ensureServiceReady(value=>states.push(value)),/pilot configuration/);
 assert.equal(calls,1);assert.deepEqual(states,[true,false]);
});
