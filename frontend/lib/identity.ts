// Self-asserted browser label for analytics and a soft demo cap; never authentication.
let sessionDemoId = '';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function getDemoId(): string {
  if (sessionDemoId) return sessionDemoId;
  try {
    // Keep the existing browser identity so adding demo_id never resets its quota.
    const previous = localStorage.getItem('emailbuddy-device-id');
    const saved = localStorage.getItem('demo_id');
    sessionDemoId = previous && uuid.test(previous) ? previous : saved && uuid.test(saved) ? saved : '';
  } catch { /* Storage is optional. Keep one ID in memory for this page. */ }
  if (!sessionDemoId) sessionDemoId = crypto.randomUUID();
  for (const key of ['emailbuddy-device-id', 'demo_id']) {
    try { localStorage.setItem(key, sessionDemoId); } catch { /* Private browsing may deny storage. */ }
  }
  return sessionDemoId;
}

// Existing callers and demo requests must use the same identity.
export const deviceId = getDemoId;
