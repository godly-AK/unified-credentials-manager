import type { Metadata } from 'next';
import '../styles/globals.css';
import Navbar from '../components/Navbar';

// A fresh CSP script nonce is attached to each request by middleware.
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: { default: 'UCM | Your account, protected', template: '%s | UCM' },
  description: 'A self-hosted account portal with secure sign-in, device recovery, and session controls.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <div className="page">{children}</div>
        <footer className="site-footer">
          <span>Unified Credentials Manager</span>
          <span>Self-hosted authentication. Your infrastructure.</span>
        </footer>
      </body>
    </html>
  );
}
