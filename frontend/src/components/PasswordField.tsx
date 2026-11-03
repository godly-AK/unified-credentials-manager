'use client';
import { useState } from 'react';

export default function PasswordField({ id, label, value, onChange, newPassword = false, hint }: {
  id: string; label: string; value: string; onChange: (value: string) => void; newPassword?: boolean; hint?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <span className="password-input">
        <input id={id} type={visible ? 'text' : 'password'} value={value}
          onChange={event => onChange(event.target.value)} required maxLength={128}
          autoComplete={newPassword ? 'new-password' : 'current-password'}
          aria-describedby={hint ? id + '-hint' : undefined} />
        <button type="button" aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? 'Hide' : 'Show'}</button>
      </span>
      {hint && <small id={id + '-hint'}>{hint}</small>}
    </div>
  );
}
