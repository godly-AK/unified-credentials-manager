// Components/Navbar.tsx
import Link from 'next/link';

const Navbar = () => {
  return (
    <nav className="bg-gray-950 p-4 fixed top-0 w-full z-50">
      <div className="container mx-auto flex justify-between items-center">
        {/* Brand */}
        <div className="text-white font-bold text-xl">Net Knights</div>

        {/* Navigation Links */}
        <div className="flex space-x-4">
          <Link
            href="/services"
            className="text-white px-4 py-2 hover:text-cyan-300 transition-colors"
          >
            Services
          </Link>
          <Link
            href="/services/attack-monitor"
            className="text-white px-4 py-2 hover:text-cyan-300 transition-colors"
          >
            Attack Monitor
          </Link>
          <Link
            href="/about"
            className="text-white px-4 py-2 hover:text-cyan-300 transition-colors"
          >
            About Us
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
