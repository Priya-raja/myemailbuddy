// Self-asserted browser label for analytics and a soft demo cap; never authentication.
let sessionDeviceId = '';
export function deviceId(): string {
  if (sessionDeviceId) return sessionDeviceId;
  try {
    const saved = localStorage.getItem('emailbuddy-device-id');
    if (saved && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(saved)) {
      sessionDeviceId = saved;
      return saved;
    }
  } catch { /* Storage is optional. Keep an ID in memory for this page. */ }
  sessionDeviceId = crypto.randomUUID();
  try { localStorage.setItem('emailbuddy-device-id', sessionDeviceId); } catch { /* Private browsing may deny storage. */ }
  return sessionDeviceId;
}
