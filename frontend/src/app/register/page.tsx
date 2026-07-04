'use client';

import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import zxcvbn from 'zxcvbn';

const Register = () => {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Password strength meter
  const strength = useMemo(() => zxcvbn(password), [password]);
  const strengthScore = strength.score; // 0-4
  const strengthLabel = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'][strengthScore];
  const strengthPercent = (strengthScore / 4) * 100;
  const strengthColor = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'][strengthScore];

  // Regex rules for password validation
  const isPasswordValid = useMemo(() => {
    return (
      password.length >= 8 &&
      /[A-Z]/.test(password) &&
      /[a-z]/.test(password) &&
      /[0-9]/.test(password) &&
      /[!@#$%^&*(),.?":{}|<>]/.test(password)
    );
  }, [password]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!username || !email || !password || !confirmPassword) {
      setError('All fields are required.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!isPasswordValid) {
      setError('Password does not meet required security criteria.');
      return;
    }

    try {
      // Send secure POST request to backend
      const response = await axios.post('http://localhost:8000/api/register', {
        username,
        password,
        email,
      });

      if (response.data.success) {
        setMessage('Registration successful! Redirecting to login...');
        setTimeout(() => router.push('/login'), 1500);
      } else {
        const msg =
        typeof response.data.message === 'string'
        ? response.data.message
        : response.data.message?.error || 'Registration failed.';
        setError(msg);
      }
    } catch (err: any) {
      console.error(err);
      setError(
        err.response?.data?.message?.error || err.response?.data?.message || 'An unexpected error occurred.'
      );
    }
  };

  return (
    <div className="flex justify-center mt-10 px-4">
    <div className="w-full max-w-md">
    <div className="bg-gray-900 border border-green-400 rounded-lg shadow-lg p-6">
    <div className="text-center mb-6">
    <h2 className="font-bitcount text-3xl font-bold text-green-400">Register</h2>
    </div>

    <form onSubmit={handleSubmit} className="space-y-4">
    {/* Username */}
    <div>
    <label htmlFor="username" className="block mb-1 font-semibold text-green-400">Username</label>
    <input
    type="text"
    id="username"
    placeholder="Choose a username"
    required
    value={username}
    onChange={(e) => setUsername(e.target.value)}
    className="font-bitcount w-full px-3 py-2 rounded border border-green-400 bg-gray-800 text-green-400 focus:outline-none focus:ring-2 focus:ring-green-400"
    />
    </div>

    {/* Email */}
    <div>
    <label htmlFor="email" className="block mb-1 font-semibold text-green-400">Email</label>
    <input
    type="email"
    id="email"
    placeholder="Enter your email"
    required
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    className="font-bitcount w-full px-3 py-2 rounded border border-green-400 bg-gray-800 text-green-400 focus:outline-none focus:ring-2 focus:ring-green-400"
    />
    </div>

    {/* Password */}
    <div>
    <label htmlFor="password" className="block mb-1 font-semibold text-green-400">Password</label>
    <input
    type="password"
    id="password"
    placeholder="Enter your password"
    required
    value={password}
    onChange={(e) => setPassword(e.target.value)}
    className="font-bitcount w-full px-3 py-2 rounded border border-green-400 bg-gray-800 text-green-400 focus:outline-none focus:ring-2 focus:ring-green-400"
    />

    {/* Strength meter */}
    {password && (
      <div className="mt-2">
      <div className="w-full bg-gray-700 h-2 rounded">
      <div
      className={`h-2 rounded ${strengthColor}`}
      style={{ width: `${strengthPercent}%`, transition: 'width 0.3s ease' }}
      ></div>
      </div>
      <p className="text-sm mt-1 text-green-400 font-bitcount">Strength: {strengthLabel}</p>
      </div>
    )}

    {/* Checklist */}
    <ul className="text-xs text-gray-400 mt-2 space-y-1 font-bitcount">
    <li className={password.length >= 8 ? 'text-green-400' : 'text-red-400'}>• Minimum 8 characters</li>
    <li className={/[A-Z]/.test(password) ? 'text-green-400' : 'text-red-400'}>• At least one uppercase letter</li>
    <li className={/[a-z]/.test(password) ? 'text-green-400' : 'text-red-400'}>• At least one lowercase letter</li>
    <li className={/[0-9]/.test(password) ? 'text-green-400' : 'text-red-400'}>• At least one number</li>
    <li className={/[!@#$%^&*(),.?":{}|<>]/.test(password) ? 'text-green-400' : 'text-red-400'}>• At least one special character</li>
    </ul>
    </div>

    {/* Confirm password */}
    <div>
    <label htmlFor="confirm_password" className="block mb-1 font-semibold text-green-400">Confirm Password</label>
    <input
    type="password"
    id="confirm_password"
    placeholder="Confirm your password"
    required
    value={confirmPassword}
    onChange={(e) => setConfirmPassword(e.target.value)}
    className="font-bitcount w-full px-3 py-2 rounded border border-green-400 bg-gray-800 text-green-400 focus:outline-none focus:ring-2 focus:ring-green-400"
    />
    </div>

    {/* Messages */}
    {error && <p className="text-red-500 text-center">{error}</p>}
    {message && <p className="text-green-400 text-center">{message}</p>}

    {/* Submit button */}
    <button
    type="submit"
    disabled={!isPasswordValid}
    className={`font-bitcount w-full px-4 py-2 rounded font-bold transition duration-300 ${
      isPasswordValid ? 'bg-green-400 text-black hover:bg-green-500' : 'bg-gray-700 text-gray-500 cursor-not-allowed'
    }`}
    >
    Register
    </button>
    </form>

    <p className="text-center mt-4">
    <a href="/login" className="font-bitcount text-green-400 hover:text-green-500">
    Already have an account? Login
    </a>
    </p>
    </div>
    </div>
    </div>
  );
};

export default Register;
