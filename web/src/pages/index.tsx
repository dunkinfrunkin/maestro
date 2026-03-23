import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

const PHASES = [
  { status: 'Issue', color: '#8a7e6b', log: 'GitHub Issue #47: Add POST /payments/refund endpoint' },
  { status: 'Implement', color: '#5c7cba', log: 'Reading src/services/stripe.ts\nAdding refund endpoint with validation\nTests: 8 passed\nPR #142 created' },
  { status: 'Review', color: '#8b6bb5', log: 'stripe.ts:47 — missing idempotency key\nREVIEW_VERDICT: REQUEST_CHANGES' },
  { status: 'Implement', color: '#5c7cba', log: 'Fixed: added idempotency_key parameter\nReplied to comment thread\ngit push' },
  { status: 'Review', color: '#8b6bb5', log: 'Verified — fix looks good\nThread resolved\nREVIEW_VERDICT: APPROVE' },
  { status: 'Risk', color: '#b58840', log: 'Scope 2/5 | Blast 2/5 | Complexity 1/5\nRISK_LEVEL: LOW — auto-approved' },
  { status: 'Deploy', color: '#b5a040', log: 'CI: 4/4 passing\nMerged via squash\nDeploy: completed' },
  { status: 'Monitor', color: '#5ba870', log: 'Error rate: 0.02%\nNo P0/P1 issues\nSTATUS: HEALTHY' },
];

const FEATURES = [
  ['Autonomous pipeline', 'Tickets flow through implement, review, risk, deploy, and monitor — each handled by a dedicated Claude Code agent.'],
  ['PR conversations', 'Agents post inline comments and reply in threads. Review resolves conversations via GitHub API when fixes are verified.'],
  ['Risk scoring', 'Seven-dimension risk assessment before every deploy. Configurable auto-approve threshold per workspace.'],
  ['Configurable agents', 'Each agent has its own system prompt, model selection, and settings. Edit prompts directly in the dashboard.'],
  ['GitHub and Linear', 'Pull issues from either tracker. Connections stored with encrypted tokens. Access all repos or filter specific ones.'],
  ['Plugin framework', 'Build custom agents by subclassing AgentPlugin. Register via Python entry points or drop files in a plugins directory.'],
];

export default function Home() {
  return (
    <Layout title="Maestro" description="Autonomous coding agent orchestration for enterprise teams">

      {/* Hero */}
      <section style={{ padding: '6rem 1.5rem 4rem', textAlign: 'center' }}>
        <div style={{ maxWidth: 640, margin: '0 auto' }}>
          <img src="/img/logo.png" alt="" style={{ width: 100, height: 100, marginBottom: '1.5rem' }} />
          <h1 style={{
            fontSize: 'clamp(2.5rem, 5vw, 3.5rem)', fontWeight: 800, letterSpacing: '-0.05em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: '0 0 1rem', lineHeight: 1.05,
          }}>
            Your codebase,<br />orchestrated.
          </h1>
          <p style={{ fontSize: '1.1rem', color: 'var(--ma-muted)', lineHeight: 1.6, margin: '0 0 2rem' }}>
            AI agents that implement, review, and deploy your tickets.
          </p>
          <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center', marginBottom: '0.75rem' }}>
            <Link to="/docs/getting-started" style={{
              padding: '0.65rem 1.5rem', fontSize: '0.85rem', borderRadius: '0.375rem',
              background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 600, textDecoration: 'none',
            }}>Get started</Link>
            <Link to="https://github.com/dunkinfrunkin/maestro" style={{
              padding: '0.65rem 1.5rem', fontSize: '0.85rem', borderRadius: '0.375rem',
              background: 'transparent', color: 'var(--ma-fg)', fontWeight: 500,
              border: '1px solid var(--ma-border)', textDecoration: 'none',
            }}>View source</Link>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--ma-muted)' }}>Under active development</span>
        </div>
      </section>

      {/* Pipeline — vertical timeline */}
      <section style={{ maxWidth: 540, margin: '0 auto', padding: '0 1.5rem 4rem' }}>
        <h2 style={{
          fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
          color: 'var(--ma-fg)', textAlign: 'center', marginBottom: '2.5rem',
        }}>
          From issue to production
        </h2>

        <div style={{ position: 'relative', paddingLeft: '2rem' }}>
          {/* Vertical line */}
          <div style={{
            position: 'absolute', left: '0.45rem', top: 0, bottom: 0, width: 2,
            background: 'var(--ma-border)',
          }} />

          {PHASES.map((phase, i) => (
            <div key={i} style={{ position: 'relative', marginBottom: i < PHASES.length - 1 ? '1.25rem' : 0 }}>
              {/* Dot */}
              <div style={{
                position: 'absolute', left: '-1.7rem', top: '0.55rem',
                width: 10, height: 10, borderRadius: '50%',
                background: phase.color, border: '2px solid var(--ma-bg)',
                boxShadow: `0 0 0 2px ${phase.color}33`,
              }} />
              {/* Card */}
              <div style={{
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
                borderRadius: '0.5rem', padding: '0.7rem 0.85rem',
              }}>
                <span style={{
                  fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
                  letterSpacing: '0.06em', color: phase.color,
                }}>
                  {phase.status}
                </span>
                <pre style={{
                  margin: '0.35rem 0 0', padding: 0, background: 'none', border: 'none',
                  fontSize: '0.68rem', fontFamily: 'var(--ifm-font-family-monospace)',
                  color: 'var(--ma-muted)', lineHeight: 1.6, whiteSpace: 'pre-wrap', overflow: 'hidden',
                }}>
                  {phase.log}
                </pre>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Full-width break */}
      <section style={{ background: '#1a1612', padding: '3.5rem 1.5rem' }}>
        <div style={{ maxWidth: 640, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif", color: '#e8e0d4', margin: '0 0 0.5rem' }}>
            Powered by Claude Code
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#a89880', lineHeight: 1.6, margin: '0 0 1.5rem' }}>
            Each agent runs as a Claude Code CLI subprocess with full access to
            Read, Write, Edit, Bash, Glob, and Grep. Configurable model per agent.
          </p>
          <code style={{ fontSize: '0.75rem', color: '#c4a882', fontFamily: 'var(--ifm-font-family-monospace)' }}>
            $ claude -p "..." --model claude-sonnet-4-6 --output-format stream-json
          </code>
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 760, margin: '0 auto', padding: '4rem 1.5rem 3rem' }}>
        <h2 style={{
          fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
          color: 'var(--ma-fg)', textAlign: 'center', marginBottom: '2rem',
        }}>
          Built for teams that ship
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          {FEATURES.map(([title, desc]) => (
            <div key={title} style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.3rem' }}>
                {title}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--ma-muted)', lineHeight: 1.6 }}>
                {desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Stack + CTA */}
      <section style={{ maxWidth: 640, margin: '0 auto', padding: '0 1.5rem 5rem', textAlign: 'center' }}>
        <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
          {['Python / FastAPI', 'Next.js', 'PostgreSQL', 'Claude Code CLI', 'GitHub', 'Linear'].map((s) => (
            <span key={s} style={{
              fontSize: '0.65rem', padding: '0.2rem 0.55rem', borderRadius: 9999,
              background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
            }}>{s}</span>
          ))}
        </div>
        <Link to="/docs/getting-started" style={{
          padding: '0.65rem 1.5rem', fontSize: '0.85rem', borderRadius: '0.375rem',
          background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 600, textDecoration: 'none',
        }}>Get started</Link>
      </section>
    </Layout>
  );
}
