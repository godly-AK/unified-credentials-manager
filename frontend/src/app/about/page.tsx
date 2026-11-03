import Link from 'next/link';

export default function About() {
  return (
    <main>
      <section className="project-hero">
        <h1>Authentication you can host yourself.</h1>
        <p className="lead">UCM brings registration, sign-in, account controls, and device recovery into one reusable service. The portal you are using is its first integration example.</p>
        <div className="panel-actions"><Link className="btn" href="/register">Create an account</Link><Link className="btn secondary" href="/login">Try the portal</Link></div>
      </section>
      <section className="feature-row">
        <article><h2>Better password handling</h2><p>Long passphrases, local common-password screening, Argon2id storage, and protection against recent password reuse.</p></article>
        <article><h2>Access you control</h2><p>Review active sessions and sign out another device. Password changes end existing sessions and require a fresh sign-in.</p></article>
        <article><h2>A key on your phone</h2><p>The native Android app enrolls a device key and uses biometric approval to authorize password recovery.</p></article>
      </section>
      <section className="panel"><h2>Built in the open</h2><p className="lead" style={{ marginTop: 15 }}>This is a lab development release. NIST password guidance and OWASP application controls guide its implementation. Production transport, broader security validation, and the external website integration example remain on the delivery plan.</p></section>
    </main>
  );
}
