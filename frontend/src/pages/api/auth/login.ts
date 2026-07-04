import type { NextApiRequest, NextApiResponse } from 'next';
 import { users } from '../../../lib/users';
  export default function handler(req: NextApiRequest, res: NextApiResponse) { if (req.method === 'POST') { const { username, password } = req.body;
   const user = users.find(u => u.username === username && u.password === password);
    if (user) { return res.status(200).json({ success: true });
 } else {
     return res.status(200).json({ success: false, message: 'Invalid credentials' });
 } 
} else {
     res.status(405).end(); 
    } 
}