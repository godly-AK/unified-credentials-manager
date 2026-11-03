export default function AuthShell({ title, description, children }: {
  title: string; description: string; children: React.ReactNode;
}) {
  return (
    <main className="auth-grid">
      <section className="auth-intro">
        <span className="eyebrow">Account setup</span>
        <h1>{title}</h1>
        <p className="lead">{description}</p>
        <div className="auth-proof">
          <span>01 &nbsp; Create your account</span>
          <span>02 &nbsp; Enroll your phone</span>
          <span>03 &nbsp; Approve access</span>
        </div>
      </section>
      <section className="form-panel">{children}</section>
    </main>
  );
}
