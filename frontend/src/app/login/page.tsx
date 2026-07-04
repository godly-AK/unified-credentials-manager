'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

interface LoginResponse {
  success: boolean;
  data?: any;
  message?: string;
  token?: string;
}

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const getClientInfo = async () => {
    try {
      const ipResponse = await axios.get('https://api.ipify.org?format=json');
      const ip = ipResponse.data.ip;
      const headers = {
        'User-Agent': navigator.userAgent,
        'Accept-Language': navigator.language,
      };
      const time = new Date().toISOString();
      return { ip, headers, time };
    } catch (err) {
      return { ip: 'unknown', headers: {}, time: new Date().toISOString() };
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    try {
      const { ip: last_ip_addr, headers, time: last_access_time } = await getClientInfo();

      const response = await axios.post<LoginResponse>(
        'http://localhost:8000/api/login',
        { username, password, last_ip_addr, headers, last_access_time }
      );

      const resData = response.data;

      if (resData.success) {
        if (resData.token) localStorage.setItem('token', resData.token);
        router.push('/services');
      } else {
        // Ensure message is always a string
        setError(typeof resData.message === 'string' ? resData.message : JSON.stringify(resData.message));
      }
    } catch (err: any) {
      console.error(err);
      setError('An error occurred. Please try again.');
    }
  };

  return (
    <div className="flex justify-center mt-10 px-4">
    <div className="w-full max-w-md">
    <div className="bg-gray-900 border border-green-400 rounded-lg shadow-lg p-6">
    <div className="text-center mb-6">
    <h2 className="font-bitcount text-3xl font-bold text-green-400">Login</h2>
    </div>

    <form onSubmit={handleSubmit} className="space-y-4">
    <div>
    <label htmlFor="username" className="block mb-1 font-bitcount font-semibold text-green-400">Username</label>
    <input
    type="text"
    id="username"
    placeholder="Your username"
    required
    value={username}
    onChange={e => setUsername(e.target.value)}
    className="w-full px-3 py-2 rounded border border-green-400 bg-gray-800 text-green-400 focus:outline-none focus:ring-2 focus:ring-green-400"
    />
    </div>

    <div>
    <label htmlFor="password" className="block mb-1 font-bitcount font-semibold text-green-400">Password</label>
    <input
    type="password"
    id="password"
    placeholder="Your password"
    required
    value={password}
    onChange={e => setPassword(e.target.value)}
    className="w-full px-3 py-2 rounded border border-green-400 bg-gray-800 text-green-400 focus:outline-none focus:ring-2 focus:ring-green-400"
    />
    </div>

    {error && <p className="text-red-500 text-center">{error}</p>}

    <button
    type="submit"
    className="w-full px-4 py-2 bg-green-400 text-black font-bold rounded hover:bg-green-500 transition duration-300"
    >
    Login
    </button>
    </form>

    <p className="font-bitcount text-center mt-4">
    <a href="/register" className="text-orange-400 hover:text-orange-300 transition">
    Register instead
    </a>
    </p>
    </div>
    </div>
    </div>
  );
};

export default Login;
