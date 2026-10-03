'use client';

// Registers public/sw.js in production builds only (the dev server's assets are not hashed).
import { useEffect } from 'react';

export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' || !('serviceWorker' in navigator)) return;
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {
      // The app works without the service worker; nothing to tell the user.
    });
  }, []);
  return null;
}
