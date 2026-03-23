import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

const PIPELINE_STEPS = [
  { name: 'Queued', desc: 'Ticket enters the pipeline' },
  { name: 'Implement', desc: 'Agent writes code, creates PR' },
  { name: 'Review', desc: 'Agent reviews PR, posts inline comments' },
  { name: 'Risk Profile', desc: 'Agent scores deployment risk' },
  { name: 'Deploy', desc: 'Agent merges PR, monitors CI' },
  { name: 'Monitor', desc: 'Agent checks post-deploy health' },
];

const EXAMPLE = [
  { agent: 'Implementation Agent', text: 'Reading src/router.js. Adding GET /books/search route before the /:id handler. Running tests — 6 passed. Pushing branch, creating PR #24.' },
  { agent: 'Review Agent', text: 'src/books.test.js line 31 — Test named "returns multiple matches" asserts length === 1. Misleading.' },
  { agent: 'Implementation Agent', text: 'Fixed: Changed query to match 2 books. Updated assertion. Replied to comment thread.' },
  { agent: 'Review Agent', text: 'Verified — fix looks good. Thread resolved. APPROVE.' },
  { agent: 'Risk Profile Agent', text: 'Scope 1/5, Blast Radius 1/5, Complexity 1/5. Risk level: LOW. Auto-approved.' },
];

const FEATURES = [
  ['Multi-agent pipeline', 'Five agents in sequence — each owns one stage of the development lifecycle.'],
  ['Inline PR reviews', 'Comments on specific lines. Implementation agent replies with fixes in the same thread.'],
  ['Configurable per agent', 'Each agent has its own prompt, model, and settings. Edit directly in the dashboard.'],
  ['GitHub and Linear', 'Pull issues from either tracker. Encrypted token storage per workspace.'],
  ['Risk scoring', 'Seven-dimension risk assessment. Configurable auto-approve threshold.'],
  ['Enterprise plugins', 'Extend with custom agents via Python entry points or a plugins directory.'],
];

export default function Home() {
  return (
    <Layout title="Maestro" description="Autonomous coding agent orchestration for enterprise teams">
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 1.5rem' }}>

        {/* Hero */}
        <section style={{ paddingTop: '5rem', paddingBottom: '3rem', textAlign: 'center' }}>
          <span style={{
            display: 'inline-block', fontSize: '0.7rem', fontWeight: 500,
            padding: '0.3rem 0.7rem', borderRadius: 9999,
            background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
          }}>
            Under active development
          </span>
          <h1 style={{
            fontSize: '3rem', fontWeight: 700, letterSpacing: '-0.04em',
            color: 'var(--ma-fg)', margin: '1.25rem 0 0.75rem',
          }}>
            Maestro
          </h1>
          <p style={{ fontSize: '1.1rem', color: 'var(--ma-muted)', lineHeight: 1.6, maxWidth: 520, margin: '0 auto 2rem' }}>
            Autonomous coding agents that implement, review, and deploy your tickets.
            Inspired by{' '}
            <a href="https://github.com/openai/symphony" style={{ color: 'var(--ma-accent)', textDecoration: 'underline' }}>Symphony</a>.
          </p>
          <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center' }}>
            <Link to="/docs/getting-started" style={{
              padding: '0.55rem 1.25rem', fontSize: '0.8rem', borderRadius: '0.375rem',
              background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 500, textDecoration: 'none',
            }}>
              Documentation
            </Link>
            <Link to="https://github.com/dunkinfrunkin/maestro" style={{
              padding: '0.55rem 1.25rem', fontSize: '0.8rem', borderRadius: '0.375rem',
              background: 'transparent', color: 'var(--ma-fg)', fontWeight: 500,
              border: '1px solid var(--ma-border)', textDecoration: 'none',
            }}>
              View source
            </Link>
          </div>
        </section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--ma-border)', margin: '0 0 3rem' }} />

        {/* Pipeline */}
        <section style={{ paddingBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.35rem' }}>
            Pipeline
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', marginBottom: '1.5rem' }}>
            Each stage is handled by a dedicated agent. Review loops until all comments are resolved.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem' }}>
            {PIPELINE_STEPS.map((s, i) => (
              <div key={s.name} style={{
                padding: '0.75rem 0.5rem', textAlign: 'center',
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
                borderRadius: '0.375rem',
              }}>
                <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.15rem' }}>
                  {s.name}
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--ma-muted)', lineHeight: 1.4 }}>{s.desc}</div>
              </div>
            ))}
          </div>
        </section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--ma-border)', margin: '0 0 3rem' }} />

        {/* Example */}
        <section style={{ paddingBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.35rem' }}>
            How it works
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', marginBottom: '1.5rem' }}>
            A ticket moves through the pipeline. Agents communicate through PR comment threads.
          </p>
          <div style={{ borderLeft: '2px solid var(--ma-border)', paddingLeft: '1.25rem', marginLeft: '0.25rem' }}>
            {EXAMPLE.map((e, i) => (
              <div key={i} style={{ marginBottom: '1rem', position: 'relative' }}>
                <div style={{
                  position: 'absolute', left: '-1.55rem', top: '0.3rem',
                  width: 7, height: 7, borderRadius: '50%', background: 'var(--ma-accent)',
                }} />
                <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.2rem' }}>
                  {e.agent}
                </div>
                <div style={{
                  fontSize: '0.72rem', color: 'var(--ma-muted)',
                  background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
                  borderRadius: '0.375rem', padding: '0.5rem 0.7rem',
                  fontFamily: 'var(--ifm-font-family-monospace)', lineHeight: 1.5,
                }}>
                  {e.text}
                </div>
              </div>
            ))}
          </div>
        </section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--ma-border)', margin: '0 0 3rem' }} />

        {/* Features */}
        <section style={{ paddingBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '1.25rem' }}>
            Features
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            {FEATURES.map(([title, desc]) => (
              <div key={title} style={{
                padding: '1rem', background: 'var(--ma-surface)',
                border: '1px solid var(--ma-border)', borderRadius: '0.375rem',
              }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.2rem' }}>
                  {title}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--ma-muted)', lineHeight: 1.5 }}>
                  {desc}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Stack */}
        <section style={{ paddingBottom: '4rem', textAlign: 'center' }}>
          <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            {['Python / FastAPI', 'Next.js', 'PostgreSQL', 'Claude Code CLI', 'GitHub', 'Linear'].map((s) => (
              <span key={s} style={{
                fontSize: '0.65rem', padding: '0.2rem 0.55rem', borderRadius: 9999,
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
              }}>
                {s}
              </span>
            ))}
          </div>
        </section>

      </div>
    </Layout>
  );
}
