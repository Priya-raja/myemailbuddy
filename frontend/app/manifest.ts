import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'My Email Buddy',
    short_name: 'Email Buddy',
    description: 'Write clear English messages for work and school in your own language.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#fafbf7',
    theme_color: '#287354',
    lang: 'en',
    categories: ['productivity', 'utilities'],
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}
