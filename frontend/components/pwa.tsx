'use client';

import { useEffect, useState } from 'react';
import { Download, X } from 'lucide-react';

interface InstallPrompt extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function Pwa() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [installed, setInstalled] = useState(true);
  const [instructions, setInstructions] = useState(false);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const standalone = window.matchMedia('(display-mode: standalone)');
    const updateInstalled = () => setInstalled(standalone.matches || !!(navigator as Navigator & { standalone?: boolean }).standalone);
    const updateConnection = () => setOffline(!navigator.onLine);
    const onPrompt = (event: Event) => { event.preventDefault(); setPrompt(event as InstallPrompt); };
    const onInstalled = () => { setInstalled(true); setInstructions(false); setPrompt(null); };
    updateInstalled();
    updateConnection();
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    window.addEventListener('online', updateConnection);
    window.addEventListener('offline', updateConnection);
    standalone.addEventListener('change', updateInstalled);
    // Keep development reloads free of worker caches. Verify offline behavior with next start.
    if (process.env.NODE_ENV === 'production' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' }).catch(() => {
        // Installation remains optional; the writing flow still works without a worker.
      });
    }
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
      window.removeEventListener('online', updateConnection);
      window.removeEventListener('offline', updateConnection);
      standalone.removeEventListener('change', updateInstalled);
    };
  }, []);

  async function install() {
    if (!prompt) { setInstructions(true); return; }
    try {
      await prompt.prompt();
      const choice = await prompt.userChoice;
      if (choice.outcome === 'accepted') setInstalled(true);
    } catch { setInstructions(true); }
    finally { setPrompt(null); }
  }

  return <>
    {offline && <div className="offline-status" role="status">You&apos;re offline. Reconnect to generate a draft or transcribe audio. Your current text stays on this screen.</div>}
    {!installed && <button className="install-app" onClick={install}><Download size={15} aria-hidden="true" /> Install app</button>}
    {instructions && <div className="install-help" role="dialog" aria-label="Install My Email Buddy">
      <button className="install-close" aria-label="Close install instructions" onClick={() => setInstructions(false)}><X size={17}/></button>
      <strong>Keep your buddy close</strong>
      <p>In Chrome or Edge, open the browser menu and choose <b>Install app</b>.</p>
      <p>On iPhone or iPad, open this page in Safari, tap <b>Share</b>, then <b>Add to Home Screen</b>. On Mac, use Safari&apos;s <b>Add to Dock</b>.</p>
    </div>}
  </>;
}
