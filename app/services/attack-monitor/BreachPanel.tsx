'use client';

import { useRouter } from 'next/navigation';

interface Props {
  triggerBreach: () => void;
}

export default function BreachPanel({ triggerBreach }: Props) {
  const router = useRouter();

  const handleLogout = () => {
    // Clear any stored auth tokens or session data
    localStorage.removeItem('token');
    // Redirect to login page
    router.push('/login');
  };

  return (
    <div className="bg-[#101826] p-4 rounded-xl shadow-[0_0_15px_rgba(255,0,0,0.5)]">
      <h2 className="text-lg font-semibold mb-2 text-white">Simulate Breach</h2>
      <button
        onClick={triggerBreach}
        className="w-full bg-[#ff4d4d] py-2 rounded-lg font-semibold hover:bg-red-500 transition"
      >
        Trigger Breach
      </button>
      <button
        onClick={handleLogout}
        className="w-full mt-3 border border-gray-500 py-2 rounded-lg hover:bg-gray-700 transition text-white"
      >
        Logout
      </button>
    </div>
  );
}
