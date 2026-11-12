import Link from 'next/link';

export default function About() {
  return (
    <main>
      <section className="project-hero">
        <h1>Identity and access, under your control.</h1>
        <p className="lead">UCM is a self-hosted authentication prototype with phone approval, signed workplace witnesses, and server-enforced access levels.</p>
        <div className="panel-actions"><Link className="btn" href="/register">Create an account</Link><Link className="btn secondary" href="/login">Try the portal</Link></div>
      </section>
      <section className="feature-row">
        <article><h2>Better password handling</h2><p>Long passphrases, local common-password screening, Argon2id storage, and protection against recent password reuse.</p></article>
        <article><h2>Access you control</h2><p>Review active sessions and sign out another device. Password changes end existing sessions and require a fresh sign-in.</p></article>
        <article><h2>A key on your phone</h2><p>The Android authenticator signs fresh requests with a device-held key, after biometric approval for the main phone.</p></article>
      </section>
      <section className="panel"><h2>Built in the open</h2><p className="lead" style={{ marginTop: 15 }}>This prototype applies selected NIST and OWASP guidance. A sample website demonstrates a trusted same-site integration. Device compatibility, broader security testing, and production operations continue to be evaluated.</p></section>
    </main>
  );
}
