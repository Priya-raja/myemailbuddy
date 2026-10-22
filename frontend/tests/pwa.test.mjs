import { readFileSync, existsSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
const source = readFileSync(new URL('../public/sw.js', import.meta.url), 'utf8');
function worker(fetchImpl=async()=>new Response('network')) {
  const handlers={},added=[],removed=[];
  const context={
    self:{location:{origin:'https://buddy.test'},addEventListener:(type,fn)=>{handlers[type]=fn;},skipWaiting:async()=>{},clients:{claim:async()=>{}}},
    caches:{open:async()=>({addAll:async urls=>added.push(...urls)}),keys:async()=>['emailbuddy-static-old','other-app'],delete:async key=>removed.push(key),match:async()=>new Response('offline page')},
    fetch:fetchImpl, URL, Response,
  };
  vm.runInNewContext(source,context);
  return {handlers,added,removed};
}
test('worker precaches only static resources that exist',async()=>{
 const {handlers,added}=worker();let done;
 handlers.install({waitUntil:promise=>{done=promise;}});await done;
 assert.ok(added.includes('/offline.html'));
 assert.ok(added.every(url=>!url.startsWith('/api')&&url!=='/'));
 for(const url of added)assert.ok(existsSync(new URL(`../public${url}`,import.meta.url)));
});
test('worker does not intercept API, audio, external or arbitrary GET requests',()=>{
 const {handlers}=worker();
 for(const request of [
  {method:'POST',url:'https://buddy.test/api/draft'},
  {method:'GET',url:'https://buddy.test/api/transcribe'},
  {method:'GET',url:'https://api.groq.com/data'},
  {method:'GET',url:'https://buddy.test/messages'},
 ]) handlers.fetch({request,respondWith:()=>assert.fail('private request intercepted')});
});
test('offline navigation gets static fallback',async()=>{
 const {handlers}=worker(async()=>{throw new Error('offline');});let reply;
 handlers.fetch({request:{method:'GET',url:'https://buddy.test/',mode:'navigate'},respondWith:value=>{reply=value;}});
 assert.equal(await (await reply).text(),'offline page');
});
test('worker only deletes its own obsolete caches',async()=>{
 const {handlers,removed}=worker();let done;
 handlers.activate({waitUntil:value=>{done=value;}});await done;
 assert.deepEqual(removed,['emailbuddy-static-old']);
});
