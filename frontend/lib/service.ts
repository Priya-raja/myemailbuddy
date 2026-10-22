// Audio and writing requests go directly to FastAPI, never through a Vercel function.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
let readyUntil = 0;
let waking: Promise<void> | null = null;

export async function ensureServiceReady(onStarting?: (value: boolean) => void): Promise<void> {
  if (Date.now() < readyUntil) return;
  onStarting?.(true);
  try {
    if (!waking) {
      waking = (async () => {
        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
          try {
            const response = await fetch(`${API_BASE}/health`, { cache: 'no-store', signal: AbortSignal.timeout(15_000) });
            if (response.ok) { readyUntil = Date.now() + 300_000; return; }
            const body = await response.json().catch(() => null);
            if (body?.status === 'not_ready') throw new Error('The service is waiting for its pilot configuration. Please contact the pilot administrator.');
          } catch (error) {
            if (error instanceof Error && error.message.includes('pilot configuration')) throw error;
          }
          await new Promise(resolve => setTimeout(resolve, 4000));
        }
        throw new Error('The service is taking longer to start. Please try again in a minute.');
      })().finally(() => { waking = null; });
    }
    await waking;
  } finally { onStarting?.(false); }
}
