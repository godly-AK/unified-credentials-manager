'use client';

import Navbar from './Navbar';
import { usePathname } from 'next/navigation';

const NavbarWrapper = () => {
  const pathname = usePathname();
  const isLoginPage = pathname === '/' || pathname === '/login';

  if (isLoginPage) return null;

  return <Navbar />;
};

export default NavbarWrapper;
