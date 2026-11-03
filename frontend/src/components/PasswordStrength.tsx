'use client';
import { useEffect, useState } from 'react';

export default function PasswordStrength({ password }: { password: string }) {
  const [score, setScore] = useState<number>();
  useEffect(() => {
    let active = true;
    if (!password) { setScore(undefined); return; }
    const timer = setTimeout(() => {
      import('zxcvbn').then(module => { if (active) setScore(module.default(password).score); });
    }, 180);
    return () => { active = false; clearTimeout(timer); };
  }, [password]);
  if (!password || score === undefined) return null;
  const labels = ['Very guessable', 'Guessable', 'Somewhat guessable', 'Good', 'Strong'];
  return <div className="strength" aria-live="polite">
    <div className="strength-track" aria-hidden="true"><span style={{ width: ((score + 1) * 20) + '%', background: score < 2 ? '#bd5765' : score < 3 ? '#9e731f' : '#1f775c' }} /></div>
    <p className="hint">Password estimate: {labels[score]}. This guide does not replace the server policy.</p>
  </div>;
}
