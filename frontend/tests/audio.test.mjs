import { readFileSync } from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
const source = readFileSync(new URL('../lib/audio.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020}}).outputText;
const {encodeWav, recordingToWav, microphoneError, MAX_RECORDING_MS} = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
test('WAV has a valid mono 16 kHz PCM header and clips samples', async()=>{
 const blob=encodeWav(new Float32Array([-2,0,2]));
 const bytes=await blob.arrayBuffer(), view=new DataView(bytes);
 assert.equal(blob.type,'audio/wav');assert.equal(bytes.byteLength,50);
 assert.equal(Buffer.from(bytes).toString('ascii',0,4),'RIFF');
 assert.equal(Buffer.from(bytes).toString('ascii',8,12),'WAVE');
 assert.equal(view.getUint32(4,true),42);assert.equal(view.getUint16(22,true),1);
 assert.equal(view.getUint32(24,true),16000);assert.equal(view.getUint32(40,true),6);
 assert.equal(view.getInt16(44,true),-32768);assert.equal(view.getInt16(46,true),0);assert.equal(view.getInt16(48,true),32767);
});
test('empty recordings are rejected before decoding',async()=>{
 await assert.rejects(recordingToWav(new Blob([])),/No audio was recorded/);
});
test('permission and device errors explain recovery',()=>{
 assert.match(microphoneError(new DOMException('denied','NotAllowedError')),/browser settings/);
 assert.match(microphoneError(new DOMException('missing','NotFoundError')),/Connect a microphone/);
 assert.equal(MAX_RECORDING_MS,25000);
});
test('conversion resamples to mono 16 kHz and closes decoder',async()=>{
 const previousAudio=globalThis.AudioContext,previousOffline=globalThis.OfflineAudioContext;
 let closed=false,started=false,connected=false;
 globalThis.AudioContext=class {async decodeAudioData(){return {length:48000,duration:1};}async close(){closed=true;}};
 globalThis.OfflineAudioContext=class {
  constructor(channels,length,rate){assert.equal(channels,1);assert.equal(length,16000);assert.equal(rate,16000);}
  createBufferSource(){return {connect(){connected=true;},start(){started=true;}};}
  async startRendering(){return {getChannelData(){return new Float32Array(16000);}};}
 };
 try{const wav=await recordingToWav(new Blob(['fake-browser-audio']));assert.equal(wav.size,32044);assert.ok(started&&connected&&closed);}
 finally{globalThis.AudioContext=previousAudio;globalThis.OfflineAudioContext=previousOffline;}
});
test('decoder is closed even when a browser recording is corrupt',async()=>{
 const previousAudio=globalThis.AudioContext;let closed=false;
 globalThis.AudioContext=class {async decodeAudioData(){throw new Error('bad audio');}async close(){closed=true;}};
 try{await assert.rejects(recordingToWav(new Blob(['corrupt'])),/bad audio/);assert.ok(closed);}
 finally{globalThis.AudioContext=previousAudio;}
});
