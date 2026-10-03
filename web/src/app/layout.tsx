import type { Metadata, Viewport } from 'next';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { ServiceWorkerRegistration } from '@/components/ServiceWorkerRegistration';
import './globals.css';

export const metadata: Metadata = {
  // No metadata title: each page renders <PageTitle> (see src/components/PageTitle.tsx).
  description: 'Upload your pickleball match video and see what we learned about it.',
  applicationName: 'Racket Analytics',
  icons: { icon: '/icons/icon.svg' },
  formatDetection: { telephone: false, email: false, address: false },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#FFFFFF' },
    { media: '(prefers-color-scheme: dark)', color: '#0F1419' },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to main content
        </a>
        <header className="site-header">
          <div className="site-header__inner">
            <Link href="/matches" className="site-header__name">
              Racket Analytics
            </Link>
          </div>
        </header>
        <main id="main" className="page" tabIndex={-1}>
          {children}
        </main>
        <footer className="site-footer">
          <p>Racket Analytics preview. Development sign-in only; do not upload real matches yet.</p>
        </footer>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
