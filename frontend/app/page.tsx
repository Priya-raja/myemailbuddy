'use client';
import { useEffect, useRef, useState } from 'react';
import { MAX_RECORDING_MS, microphoneError, recordingToWav } from '../lib/audio';
import { ArrowUpRight, AudioLines, Check, CheckCheck, ChevronRight, Copy, Heart, Mail, MessageCircle, Mic, Sparkles, Square, Users, WandSparkles } from 'lucide-react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const languages = [{code:'ta-IN',name:'Tamil',native:'தமிழ்',example:'Naalaiku personal work irukku, manager kitta one day leave kekanum.'},{code:'hi-IN',name:'Hindi',native:'हिन्दी',example:'Kal personal kaam hai, manager se ek din ki chhutti maangni hai.'},{code:'te-IN',name:'Telugu',native:'తెలుగు',example:'Repu personal pani undi, manager ni oka roju leave adagali.'},{code:'mr-IN',name:'Marathi',native:'मराठी',example:'Udya personal kaam aahe, manager la ek divas sutti magaychi aahe.'},{code:'ar',name:'Arabic',native:'العربية',example:'أريد أن أطلب من مديري إجازة ليوم غد لأمر شخصي.'}];
type Draft = { subject:string; body:string; translation:string };

async function request(path:string, body:unknown, form=false) { const response=await fetch(`${API}${path}`,{method:'POST',headers:form?undefined:{'Content-Type':'application/json'},body:form?body as FormData:JSON.stringify(body)}); const data=await response.json(); if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Please check your input and try again.'); return data; }

export default function Home(){
 const [language,setLanguage]=useState('ta-IN'),[persona,setPersona]=useState('manager'),[target,setTarget]=useState('email'),[tone,setTone]=useState('polite'),[text,setText]=useState(''),[draft,setDraft]=useState<Draft|null>(null),[busy,setBusy]=useState(''),[error,setError]=useState(''),[recording,setRecording]=useState(false),[reviewed,setReviewed]=useState(false),[stale,setStale]=useState(false),[copied,setCopied]=useState(false);
 const recorder=useRef<MediaRecorder|null>(null),stream=useRef<MediaStream|null>(null),mounted=useRef(true),recordLanguage=useRef(language),recordTimer=useRef<ReturnType<typeof setTimeout>|null>(null),starting=useRef(false);
 const selected=languages.find(l=>l.code===language)!;

 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(recordTimer.current)clearTimeout(recordTimer.current);if(recorder.current?.state!=='inactive')recorder.current?.stop();stream.current?.getTracks().forEach(t=>t.stop());};},[]);
 function resetReview(){setReviewed(false);setDraft(null);setStale(false);}
 async function generate(){setBusy('draft');setError('');try{setDraft(await request('/api/draft',{text,language,persona,target,tone}));setReviewed(false);setStale(false);}catch(e){setError((e as Error).message);}finally{setBusy('');}}
 async function record(){
  if(recording){if(recorder.current?.state==='recording')recorder.current.stop();return;}
  if(starting.current||busy)return;
  starting.current=true;setBusy('microphone');setError('');
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw new Error('Microphone recording needs localhost or HTTPS.');
   if(typeof MediaRecorder==='undefined')throw new Error('Voice recording is unavailable in this browser. Please try Chrome or Safari.');
   const media=await navigator.mediaDevices.getUserMedia({audio:true});
   if(!mounted.current){media.getTracks().forEach(t=>t.stop());return;}
   stream.current=media;recordLanguage.current=language;
   const mime=['audio/webm;codecs=opus','audio/mp4','audio/webm'].find(type=>MediaRecorder.isTypeSupported(type));
   const rec=new MediaRecorder(media,mime?{mimeType:mime}:undefined);
   recorder.current=rec;
   const chunks:BlobPart[]=[];
   let failed=false;
   rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
   rec.onerror=()=>{
    failed=true;
    if(recordTimer.current)clearTimeout(recordTimer.current);
    media.getTracks().forEach(t=>t.stop());
    if(mounted.current){setRecording(false);setBusy('');setError('Recording was interrupted. Please try again.');}
   };
   rec.onstop=async()=>{
    if(recordTimer.current)clearTimeout(recordTimer.current);
    media.getTracks().forEach(t=>t.stop());
    if(!mounted.current||failed)return;
    setRecording(false);setBusy('speech');
    try{
     const audio=await recordingToWav(new Blob(chunks,{type:rec.mimeType}));
     const form=new FormData();
     form.append('audio',audio,'recording.wav');form.append('language',recordLanguage.current);
     const data=await request('/api/transcribe',form,true);
     if(!mounted.current)return;
     if(typeof data.transcript!=='string'||!data.transcript.trim())throw new Error('No speech was detected. Please speak clearly and try again.');
     setText(old=>[old,data.transcript].filter(Boolean).join('\n'));resetReview();
    }catch(e){if(mounted.current)setError(microphoneError(e));}
    finally{if(mounted.current)setBusy('');}
   };
   rec.start();setRecording(true);setBusy('');
   recordTimer.current=setTimeout(()=>{if(rec.state==='recording')rec.stop();},MAX_RECORDING_MS);
  }catch(e){
   stream.current?.getTracks().forEach(t=>t.stop());
   if(mounted.current){setRecording(false);setBusy('');setError(microphoneError(e));}
  }finally{starting.current=false;}
 }
 async function refresh(){if(!draft)return;setBusy('translation');setError('');try{const data=await request('/api/translate',{text:[draft.subject,draft.body].filter(Boolean).join('\n\n'),language});setDraft({...draft,translation:data.translation});setStale(false);setReviewed(false);}catch(e){setError((e as Error).message);}finally{setBusy('');}}
 async function copy(){try{await navigator.clipboard.writeText(target==='email'?`Subject: ${draft!.subject}\n\n${draft!.body}`:draft!.body);setCopied(true);setTimeout(()=>setCopied(false),2000);}catch{setError('Could not copy. You can select and copy the draft manually.');}}
 function edit(key:'subject'|'body',value:string){setDraft(d=>d?{...d,[key]:value}:d);setStale(true);setReviewed(false);}
 const disabled=!!busy||recording;

 return <div className="shell"><aside className="sidebar"><a className="brand" href="/"><span className="brand-icon"><Mail size={22}/></span>myemailbuddy<span className="brand-dot">.</span></a><div className="workspace-label">YOUR LITTLE WRITING CORNER</div><div className="nav-active"><WandSparkles size={19}/> Write a message <ChevronRight size={16}/></div><div className="sidebar-note"><div className="bubble-art"><MessageCircle size={32}/><span>அ</span></div><h3>A little help.<br/>A lot more confidence.</h3><p>Your thoughts deserve to be heard. We just help you find the words.</p><div className="mini-languages">அ &nbsp; अ &nbsp; అ &nbsp; م</div></div><div className="sidebar-footer"><span className="green-dot"/> Made for your everyday conversations</div></aside>
 <div className="main"><header><span>Your words. A little clearer.</span><div className="private"><CheckCheck size={16}/> You&apos;re always in control</div></header><main><div className="eyebrow"><span/> THINK IN YOUR LANGUAGE. WRITE WITH CONFIDENCE.</div><h1>Say it your way.<br/><span>We&apos;ll find the words.</span></h1><p className="intro">An email to your manager. A quick message to a friend.<br/>Just tell us what&apos;s on your mind — in the language you call home.</p>
 <div className="editor-grid"><section className="card input-card"><div className="card-title"><span className="step">1</span><h2>What would you like to say?</h2></div><div className="field-label">I&apos;m comfortable in</div><div className="language-row">{languages.map(l=><button disabled={disabled} key={l.code} className={`language ${language===l.code?'selected':''}`} onClick={()=>{setLanguage(l.code);resetReview();}}><span lang={l.code.split('-')[0]}>{l.native}</span><small>{l.name}</small></button>)}</div><div className="text-box"><textarea aria-label="What you want to say" dir="auto" disabled={disabled} value={text} maxLength={10000} onChange={e=>{setText(e.target.value);resetReview();}} placeholder={`Type in ${selected.name}, English, or a mix of both…`}/><div className="text-bottom"><span>{recording?'Listening… tap to finish (up to 25 seconds)':busy==='microphone'?'Waiting for microphone permission…':busy==='speech'?'Turning your voice into words…':'No perfect grammar needed. Just be you.'}</span><button className={`mic ${recording?'recording':''}`} onClick={record} disabled={!!busy} aria-label={recording?'Stop recording':'Record voice'}>{recording?<Square size={17}/>:<Mic size={19}/>}</button></div></div>{error&&<div className="error" role="alert">{error}</div>}<button className="example" disabled={disabled} onClick={()=>{setText(selected.example);resetReview();}}><Sparkles size={14}/> Try an example <span>Asking for a day off ↗</span></button>
 <div className="divider"/><div className="field-label">Who are you writing to?</div><div className="segments">{[{id:'manager',label:'My manager',icon:<Users size={16}/>},{id:'colleague',label:'A colleague',icon:<Mail size={16}/>},{id:'friend',label:'A friend',icon:<Heart size={16}/>}].map(p=><button disabled={disabled} key={p.id} className={persona===p.id?'active':''} onClick={()=>{setPersona(p.id);resetReview();}}>{p.icon}{p.label}</button>)}</div><div className="settings-row"><label>Send it as<select disabled={disabled} value={target} onChange={e=>{setTarget(e.target.value);resetReview();}}><option value="email">✉ Email</option><option value="whatsapp">WhatsApp message</option></select></label><label>Make it sound<select disabled={disabled} value={tone} onChange={e=>{setTone(e.target.value);resetReview();}}>{['polite','professional','friendly','confident','brief'].map(t=><option key={t} value={t}>{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}</select></label></div><button className="generate" onClick={generate} disabled={disabled||!text.trim()}><WandSparkles size={18}/>{busy==='draft'?'Finding the right words…':'Help me write it'}<ArrowUpRight size={18}/></button><p className="under-button">You can review and change everything before sharing.</p></section>
 <section className="card output-card"><div className="card-title"><span className="step step-light">2</span><h2>Your message, ready for you</h2><span className="draft-pill">DRAFT</span></div>{!draft?<div className="empty"><div className="letter-art"><Mail size={48} strokeWidth={1.2}/><span><Sparkles size={20}/></span></div><h3>A little clarity is on its way.</h3><p>Share your thoughts on the left.<br/>Your English draft will appear right here.</p><div className="empty-chips"><span>✓ Your meaning</span><span>✓ The right tone</span><span>✓ Your final say</span></div></div>:<div className="result">{target==='email'&&<label className="draft-label">Subject<input value={draft.subject} onChange={e=>edit('subject',e.target.value)}/></label>}<label className="draft-label">English draft<textarea className="draft-body" value={draft.body} onChange={e=>edit('body',e.target.value)}/></label><div className="translation"><div><strong>Check the meaning in {selected.name}</strong><button disabled={!!busy} onClick={refresh}>{busy==='translation'?'Updating…':'Refresh translation'}</button></div>{stale?<p className="stale">You edited the English draft. Refresh the translation to check the updated meaning.</p>:<p dir="auto" lang={language.split('-')[0]}>{draft.translation}</p>}</div><label className="review"><input type="checkbox" checked={reviewed} disabled={stale||!!busy} onChange={e=>setReviewed(e.target.checked)}/> I checked the meaning and I&apos;m happy with this draft.</label><div className="actions"><button disabled={!reviewed||stale||!draft.body.trim()} onClick={copy}><Copy size={16}/>{copied?'Copied!':'Copy draft'}</button><a aria-disabled={!reviewed||stale} className={!reviewed||stale?'disabled':''} href={!reviewed||stale?undefined:target==='email'?`mailto:?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`:`https://wa.me/?text=${encodeURIComponent(draft.body)}`} target={target==='whatsapp'?'_blank':undefined} rel="noreferrer">{target==='email'?'Open email draft':'Open WhatsApp'}<ArrowUpRight size={16}/></a></div><small className="sharing-note">Your app opens a draft. Choose the recipient and send when you&apos;re ready.</small></div>}<div className="output-footer"><Check size={16}/> Always your message. Always your choice.</div></section></div>
 <div className="bottom-note"><AudioLines size={19}/><span>Speak naturally. Mix languages. Be yourself.</span><span className="bottom-languages">Tamil · Hindi · Telugu · Marathi · Arabic</span></div></main><footer>Made with a little understanding. <span>myemailbuddy</span></footer></div></div>;
}
