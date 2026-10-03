// Web app manifest (ST-010 PWA basics, AQS/STACK-04).
import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Racket Analytics',
    short_name: 'Racket',
    description: 'Upload your pickleball match video and see what we learned about it.',
    start_url: '/matches',
    scope: '/',
    display: 'standalone',
    background_color: '#FFFFFF',
    theme_color: '#0B6B4D',
    icons: [
      { src: '/icons/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
      { src: '/icons/icon-maskable.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'maskable' },
    ],
  };
}
