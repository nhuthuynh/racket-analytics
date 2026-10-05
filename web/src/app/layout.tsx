import type { Metadata, Viewport } from 'next';
import { cookies } from 'next/headers';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { AccountMenu } from '@/components/AccountMenu';
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

const SESSION_COOKIES = ['__Host-racket_session', 'racket_session'];

/** Shows the account menu when a session cookie is present. Display only: the API decides
 * whether the session is valid [AQS/SEC-03]. */
async function hasSessionCookie(): Promise<boolean> {
  const jar = await cookies();
  return SESSION_COOKIES.some((name) => jar.has(name));
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const signedIn = await hasSessionCookie();
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to main content
        </a>
        <header className="site-header">
          <div className="site-header__inner">
            <Link href={signedIn ? '/matches' : '/'} className="site-header__name">
              Racket Analytics
            </Link>
            {signedIn ? <AccountMenu /> : null}
          </div>
        </header>
        <main id="main" className="page" tabIndex={-1}>
          {children}
        </main>
        <footer className="site-footer">
          <p>Racket Analytics preview. Do not upload real matches yet.</p>
        </footer>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
