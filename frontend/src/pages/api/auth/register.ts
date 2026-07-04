// pages/api/auth/register.ts
import type { NextApiRequest, NextApiResponse } from 'next';
import { users } from '../../../lib/users';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ success: false, message: 'Username and password required' });
    }

    if (users.some(u => u.username === username)) {
      return res.status(200).json({ success: false, message: 'Username already taken' });
    }

    users.push({ username, password });
    return res.status(200).json({ success: true });
  } else {
    res.status(405).end();
  }
}
