// A-03 Signing you in… (ST-013). Client-only: the token is in the URL fragment, which never
// reaches the server, and the page loads no external assets (flows A-03).
import { AuthCallback } from '@/components/AuthCallback';

export default function AuthCallbackPage() {
  return <AuthCallback />;
}
