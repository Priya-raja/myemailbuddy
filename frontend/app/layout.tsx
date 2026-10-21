import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'My Email Buddy — Your words, with confidence', description: 'Turn your everyday thoughts into clear English emails and messages.' };
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
