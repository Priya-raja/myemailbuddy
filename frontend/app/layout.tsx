import type { Metadata, Viewport } from 'next';
import Pwa from '../components/pwa';
import './globals.css';

export const metadata: Metadata = {
  title: 'My Email Buddy — Your words, with confidence',
  description: 'Turn your everyday thoughts into clear English emails and messages.',
  applicationName: 'My Email Buddy',
  appleWebApp: { capable: true, title: 'Email Buddy', statusBarStyle: 'default' },
  icons: { icon: '/icons/icon-192.png', apple: '/icons/apple-touch-icon.png' },
};
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#287354' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}<Pwa /></body></html>;
}
