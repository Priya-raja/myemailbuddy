import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
const source=readFileSync(new URL('../lib/identity.ts',import.meta.url),'utf8');
function identity(localStorage){
 const exports={};
 const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 vm.runInNewContext(js,{exports,localStorage,crypto:{randomUUID:()=> '12345678-1234-4234-8234-123456789abc'}});
 return exports;
}
test('device ID survives page sessions without storing name or content',()=>{
 const values=new Map();const storage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)};
 const first=identity(storage).deviceId();
 assert.equal(identity(storage).deviceId(),first);
 assert.equal(values.size,2);
 assert.equal(values.get('demo_id'),first);
 assert.equal(values.get('emailbuddy-device-id'),first);
});
test('storage denial still gives a consistent page ID',()=>{
 const api=identity({getItem(){throw Error('denied')},setItem(){throw Error('denied')}});
 assert.equal(api.deviceId(),api.deviceId());
});

test('existing browser ID is reused so migration does not reset the demo counter',()=>{
 const old='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
 const values=new Map([['emailbuddy-device-id',old],['demo_id','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb']]);
 const api=identity({getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)});
 assert.equal(api.getDemoId(),old);
 assert.equal(api.deviceId(),old);
 assert.equal(values.get('demo_id'),old);
});
test('an existing demo_id is retained when there is no older device ID',()=>{
 const old='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
 const values=new Map([['demo_id',old]]);
 const storage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)};
 assert.equal(identity(storage).getDemoId(),old);
 assert.equal(identity(storage).getDemoId(),old);
 assert.equal(values.get('emailbuddy-device-id'),old);
});
