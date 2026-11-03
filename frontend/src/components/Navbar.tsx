'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { KeyRound } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname() ?? '';
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="UCM home">
        <span className="brand-mark"><KeyRound size={19} strokeWidth={2} /></span>
        UCM <span className="brand-caption">Unified Credentials Manager</span>
      </Link>
      <nav className="nav-links" aria-label="Main navigation">
        <Link className="nav-project" href="/about" aria-current={pathname === '/about' ? 'page' : undefined}>The project</Link>
        <Link href="/services" aria-current={pathname.startsWith('/services') ? 'page' : undefined}>My account</Link>
        <Link href="/services/pipeline" aria-current={pathname === '/services/pipeline' ? 'page' : undefined}>Login pipeline</Link>
        {!pathname.startsWith('/services') && <Link href="/login" aria-current={pathname === '/login' ? 'page' : undefined}>Sign in</Link>}
      </nav>
    </header>
  );
}
