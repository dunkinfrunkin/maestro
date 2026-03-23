import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

const PIPELINE_STEPS = ['Queued', 'Implement', 'Review', 'Risk Profile', 'Deploy', 'Monitor'];

const TERMINAL_LINES = [
  { time: '0:00', text: 'Cloning repository: dunkinfrunkin/test-api', type: 'dim' },
  { time: '0:02', text: 'Starting Claude Code CLI (model: claude-sonnet-4-6)', type: 'dim' },
  { time: '0:08', text: 'Reading src/router.js, src/books.js', type: 'tool' },
  { time: '0:15', text: 'Adding searchBooks() — case-insensitive filter on title and author', type: 'normal' },
  { time: '0:22', text: 'Running tests — 6 passed', type: 'success' },
  { time: '0:28', text: 'PR created: dunkinfrunkin/test-api/pull/24', type: 'accent' },
  { time: '0:30', text: 'Review: src/books.test.js:31 — misleading test name', type: 'tool' },
  { time: '0:45', text: 'Fixed: query matches 2 books, assertion updated', type: 'normal' },
  { time: '0:48', text: 'Review: verified — thread resolved. APPROVE', type: 'success' },
  { time: '0:52', text: 'Risk: LOW (1.1/5) — auto-approved for deployment', type: 'success' },
];

const FEATURES = [
  ['Multi-agent pipeline', 'Five agents in sequence — each owns one stage of the development lifecycle.'],
  ['Inline PR reviews', 'Comments on specific lines. Fixes replied in the same thread.'],
  ['Configurable per agent', 'Each agent has its own prompt, model, and settings.'],
  ['GitHub and Linear', 'Pull issues from either tracker. Encrypted token storage.'],
  ['Risk scoring', 'Seven-dimension risk assessment. Configurable auto-approve.'],
  ['Enterprise plugins', 'Extend with custom agents via Python entry points.'],
];

export default function Home() {
  return (
    <Layout title="Maestro" description="Autonomous coding agent orchestration for enterprise teams">

      {/* Hero */}
      <section style={{ position: 'relative', overflow: 'hidden', padding: '6rem 1.5rem 4rem' }}>
        {/* Grid background */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.06,
          backgroundImage: 'linear-gradient(var(--ma-accent) 1px, transparent 1px), linear-gradient(90deg, var(--ma-accent) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          maskImage: 'radial-gradient(ellipse 60% 50% at 50% 0%, black 30%, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(ellipse 60% 50% at 50% 0%, black 30%, transparent 70%)',
        }} />

        <div style={{ position: 'relative', maxWidth: 900, margin: '0 auto' }}>

          {/* Two-column hero: text left, mascot right */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3rem' }}>

            {/* Left: text */}
            <div style={{ flex: 1 }}>
              <span style={{
                display: 'inline-block', fontSize: '0.7rem', fontWeight: 500,
                padding: '0.3rem 0.7rem', borderRadius: 9999,
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
                marginBottom: '1.25rem',
              }}>
                Under active development
              </span>

              <h1 style={{
                fontSize: '3.5rem', fontWeight: 800, letterSpacing: '-0.05em',
                fontFamily: "'DM Sans', sans-serif",
                background: 'linear-gradient(135deg, var(--ma-fg) 0%, var(--ma-accent) 50%, #8b7355 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                margin: '0 0 1rem',
                lineHeight: 1.05,
              }}>
                Your codebase, orchestrated.
              </h1>

              <p style={{ fontSize: '1.1rem', color: 'var(--ma-muted)', lineHeight: 1.6, maxWidth: 440, margin: '0 0 2rem' }}>
                AI agents that implement, review, and deploy your tickets autonomously.
                From issue to production in minutes.
              </p>

              <div style={{ display: 'flex', gap: '0.6rem' }}>
            <Link to="/docs/getting-started" style={{
              padding: '0.6rem 1.4rem', fontSize: '0.8rem', borderRadius: '0.375rem',
              background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 600, textDecoration: 'none',
            }}>
              Get started
            </Link>
            <Link to="https://github.com/dunkinfrunkin/maestro" style={{
              padding: '0.6rem 1.4rem', fontSize: '0.8rem', borderRadius: '0.375rem',
              background: 'transparent', color: 'var(--ma-fg)', fontWeight: 500,
              border: '1px solid var(--ma-border)', textDecoration: 'none',
            }}>
              View source
            </Link>
          </div>
            </div>

            {/* Right: mascot */}
            <div style={{ flex: '0 0 280px', display: 'flex', justifyContent: 'center' }}>
              <img src="/img/logo.png" alt="Maestro" style={{
                width: 260, height: 260,
                filter: 'drop-shadow(0 12px 32px rgba(107,91,62,0.12))',
              }} />
            </div>
          </div>
        </div>
      </section>

      {/* Terminal demo */}
      <section style={{ maxWidth: 680, margin: '0 auto', padding: '0 1.5rem 3rem' }}>
        <div style={{
          background: '#1a1612', borderRadius: '0.75rem', overflow: 'hidden',
          border: '1px solid #2e2720',
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.15)',
        }}>
          {/* Title bar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            padding: '0.6rem 1rem', borderBottom: '1px solid #2e2720',
          }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#e85d4a', opacity: 0.8 }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#d4a73a', opacity: 0.8 }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#4ca853', opacity: 0.8 }} />
            <span style={{ marginLeft: '0.5rem', fontSize: '0.65rem', color: '#a89880', fontFamily: 'var(--ifm-font-family-monospace)' }}>
              maestro — implementation agent
            </span>
          </div>
          {/* Content */}
          <div style={{ padding: '0.75rem 1rem', maxHeight: 280, overflow: 'hidden' }}>
            {TERMINAL_LINES.map((line, i) => (
              <div key={i} style={{
                display: 'flex', gap: '0.75rem', padding: '0.15rem 0',
                fontFamily: 'var(--ifm-font-family-monospace)', fontSize: '0.7rem', lineHeight: 1.6,
              }}>
                <span style={{ color: '#5a4e3a', flexShrink: 0, width: '2rem', textAlign: 'right' }}>{line.time}</span>
                <span style={{
                  color: line.type === 'dim' ? '#6b5f4e' :
                         line.type === 'tool' ? '#8ba4c4' :
                         line.type === 'success' ? '#7da87e' :
                         line.type === 'accent' ? '#c4a882' :
                         '#b8a88e',
                }}>
                  {line.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 1.5rem' }}>

        {/* Pipeline */}
        <section style={{ paddingBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--ma-fg)', fontFamily: "'DM Sans', sans-serif", marginBottom: '0.35rem' }}>
              Harness engineering pipeline
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--ma-muted)' }}>
              Each stage is handled by a dedicated agent. Review loops until all comments are resolved.
            </p>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.25rem', flexWrap: 'wrap' }}>
            {PIPELINE_STEPS.map((s, i) => (
              <div key={s} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{
                  padding: '0.5rem 0.9rem', fontSize: '0.72rem', fontWeight: 600,
                  background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
                  borderRadius: '0.375rem', color: 'var(--ma-fg)',
                }}>
                  {s}
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <span style={{ color: 'var(--ma-border)', margin: '0 0.15rem', fontSize: '0.8rem' }}>
                    {i === 2 ? '\u21C4' : '\u2192'}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--ma-border)', margin: '0 0 3rem' }} />

        {/* Features */}
        <section style={{ paddingBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--ma-fg)', fontFamily: "'DM Sans', sans-serif", marginBottom: '1.25rem', textAlign: 'center' }}>
            Built for teams that ship
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            {FEATURES.map(([title, desc]) => (
              <div key={title} style={{
                padding: '1.1rem', background: 'var(--ma-surface)',
                border: '1px solid var(--ma-border)', borderRadius: '0.5rem',
              }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.2rem' }}>
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
