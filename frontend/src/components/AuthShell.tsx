import { LockKeyhole, ShieldCheck } from 'lucide-react';

export default function AuthShell({ title, description, children }: {
  title: string; description: string; children: React.ReactNode;
}) {
  return (
    <main className="auth-grid">
      <section className="auth-intro">
        <div className="key-art" aria-hidden="true">
          <svg viewBox="0 0 420 200" fill="none">
            <rect x="6" y="35" width="408" height="130" rx="65" fill="#e8eef9" />
            <path d="M282 63h68v32h-18v25h-28V95h-42" stroke="#aabde8" strokeWidth="13" strokeLinejoin="round" />
            <circle cx="142" cy="100" r="62" fill="white" stroke="#315de5" strokeWidth="13" />
            <circle cx="142" cy="100" r="21" stroke="#315de5" strokeWidth="10" />
            <path d="M202 100h125v24h-27v22h-28v-22h-24v-24" fill="#315de5" />
            <path d="M42 182h336" stroke="#d5dfee" strokeWidth="2" />
          </svg>
        </div>
        <h1>{title}</h1>
        <p className="lead">{description}</p>
        <div className="auth-proof">
          <span><LockKeyhole /> Private by design</span>
          <span><ShieldCheck /> Hosted by you</span>
        </div>
      </section>
      <section className="form-panel">{children}</section>
    </main>
  );
}
