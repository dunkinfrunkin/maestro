import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

const TERMINAL_LINES = [
  { time: '0:00', text: 'Cloning repository: acme/payments-api', type: 'dim' },
  { time: '0:02', text: 'Starting Claude Code CLI (model: claude-sonnet-4-6)', type: 'dim' },
  { time: '0:05', text: 'Reading src/routes/payments.ts, src/services/stripe.ts', type: 'tool' },
  { time: '0:12', text: 'Adding POST /payments/refund endpoint with validation', type: 'normal' },
  { time: '0:18', text: 'Writing tests — 8 passed', type: 'success' },
  { time: '0:22', text: 'PR #142 created: feat/refund-endpoint', type: 'accent' },
  { time: '0:25', text: 'Review: stripe.ts:47 — missing idempotency key', type: 'tool' },
  { time: '0:38', text: 'Fixed: added idempotency_key parameter', type: 'normal' },
  { time: '0:41', text: 'Review: verified. All threads resolved. APPROVE', type: 'success' },
  { time: '0:44', text: 'Risk: LOW (1.4/5) — auto-approved for deployment', type: 'success' },
  { time: '0:48', text: 'Merged via squash. CI passing. Deployed.', type: 'accent' },
];

const PHASES = [
  {
    status: 'Issue Created',
    color: '#8a7e6b',
    title: 'A ticket lands in your tracker',
    desc: 'A team member creates a GitHub issue or Linear ticket. Maestro picks it up and adds it to the pipeline.',
    log: [
      'GitHub Issue #47: "Add POST /payments/refund endpoint"',
      'Assigned to workspace: payments-team',
      'Status: Queued',
    ],
  },
  {
    status: 'Implement',
    color: '#5c7cba',
    title: 'Claude Code writes the implementation',
    desc: 'The Implementation Agent clones the repo, reads the codebase, writes the code, runs tests, and opens a pull request.',
    log: [
      'Cloning acme/payments-api...',
      'Reading src/routes/payments.ts',
      'Adding refund endpoint with Stripe API integration',
      'Writing 8 unit tests — all passing',
      'git push origin feat/refund-endpoint',
      'PR #142 created',
    ],
  },
  {
    status: 'Review',
    color: '#8b6bb5',
    title: 'Code review with inline comments',
    desc: 'The Review Agent checks out the PR branch, reads every changed file, and posts inline comments on specific lines — just like a human reviewer.',
    log: [
      'Checking out PR #142...',
      'Reading src/services/stripe.ts line 47',
      'COMMENT: Missing idempotency key for refund request',
      'COMMENT: No error handling for partial refunds',
      'REVIEW_VERDICT: REQUEST_CHANGES',
    ],
  },
  {
    status: 'Implement',
    color: '#5c7cba',
    title: 'Addressing review feedback',
    desc: 'The Implementation Agent reads each inline comment, makes the fix, and replies in the comment thread — the same workflow as human developers.',
    log: [
      'Reading inline comment #2970403242',
      'Adding idempotency_key to Stripe refund call',
      'Adding try/catch for partial refund errors',
      'Replying: "Fixed: added idempotency key and error handling"',
      'git push',
    ],
  },
  {
    status: 'Review',
    color: '#8b6bb5',
    title: 'Verified and approved',
    desc: 'The Review Agent checks each comment thread, verifies the fix in the current code, replies with confirmation, and resolves the thread.',
    log: [
      'Checking comment thread #2970403242',
      'Reading current src/services/stripe.ts:47',
      'Replying: "Verified — fix looks good"',
      'Resolving thread via GraphQL',
      'REVIEW_VERDICT: APPROVE',
    ],
  },
  {
    status: 'Risk Profile',
    color: '#b58840',
    title: 'Deployment risk assessment',
    desc: 'The Risk Profile Agent scores the PR across 7 dimensions. Low risk changes are auto-approved. Medium and above require human review.',
    log: [
      'Change Scope: 2/5  |  Blast Radius: 2/5',
      'Complexity: 1/5    |  Reversibility: 1/5',
      'Test Coverage: 1/5 |  Security: 2/5',
      'Dependencies: 1/5',
      'RISK_LEVEL: LOW (1.4/5) — auto-approved',
    ],
  },
  {
    status: 'Deploy',
    color: '#b5a040',
    title: 'Merge and monitor CI',
    desc: 'The Deployment Agent verifies CI checks, squash-merges the PR, and watches the deployment pipeline for failures.',
    log: [
      'CI checks: 4/4 passing',
      'Merging PR #142 via squash...',
      'Monitoring GitHub Actions workflow...',
      'Deploy workflow: completed',
    ],
  },
  {
    status: 'Monitor',
    color: '#5ba870',
    title: 'Post-deployment health check',
    desc: 'The Monitor Agent checks logs, error rates, and deployment status. Issues are classified by severity with rollback recommendations for critical problems.',
    log: [
      'Checking deployment status: healthy',
      'Error rate: 0.02% (baseline: 0.03%)',
      'No P0 or P1 issues detected',
      'MONITOR_STATUS: HEALTHY',
    ],
  },
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
      <section style={{ position: 'relative', overflow: 'hidden', padding: '5rem 1.5rem 3rem' }}>
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.04,
          backgroundImage: 'linear-gradient(var(--ma-accent) 1px, transparent 1px), linear-gradient(90deg, var(--ma-accent) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          maskImage: 'radial-gradient(ellipse 60% 50% at 50% 0%, black 30%, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(ellipse 60% 50% at 50% 0%, black 30%, transparent 70%)',
        }} />
        <div style={{ position: 'relative', maxWidth: 680, margin: '0 auto', textAlign: 'center' }}>
          <img src="/img/logo.png" alt="Maestro" style={{
            width: 110, height: 110, marginBottom: '1.25rem',
            filter: 'drop-shadow(0 8px 20px rgba(107,91,62,0.12))',
          }} />
          <h1 style={{
            fontSize: '3.5rem', fontWeight: 800, letterSpacing: '-0.05em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: '0 0 1rem', lineHeight: 1.05,
          }}>
            Your codebase,<br />orchestrated.
          </h1>
          <p style={{ fontSize: '1.1rem', color: 'var(--ma-muted)', lineHeight: 1.6, maxWidth: 460, margin: '0 auto 1.5rem' }}>
            AI agents that implement, review, and deploy your tickets.
            From issue to production in minutes.
          </p>
          <span style={{
            display: 'inline-block', fontSize: '0.7rem', fontWeight: 500,
            padding: '0.3rem 0.7rem', borderRadius: 9999,
            background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
            marginBottom: '2rem',
          }}>Under active development</span>
          <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center' }}>
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
        </div>
      </section>

      {/* Terminal */}
      <section style={{ maxWidth: 680, margin: '0 auto', padding: '0 1.5rem 3rem' }}>
        <div style={{
          background: '#1a1612', borderRadius: '0.75rem', overflow: 'hidden',
          border: '1px solid #2e2720', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.15)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.6rem 1rem', borderBottom: '1px solid #2e2720' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#e85d4a', opacity: 0.8 }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#d4a73a', opacity: 0.8 }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#4ca853', opacity: 0.8 }} />
            <span style={{ marginLeft: '0.5rem', fontSize: '0.65rem', color: '#a89880', fontFamily: 'var(--ifm-font-family-monospace)' }}>
              maestro pipeline
            </span>
          </div>
          <div style={{ padding: '0.75rem 1rem', maxHeight: 260, overflow: 'hidden' }}>
            {TERMINAL_LINES.map((line, i) => (
              <div key={i} style={{ display: 'flex', gap: '0.75rem', padding: '0.15rem 0', fontFamily: 'var(--ifm-font-family-monospace)', fontSize: '0.7rem', lineHeight: 1.6 }}>
                <span style={{ color: '#5a4e3a', flexShrink: 0, width: '2rem', textAlign: 'right' }}>{line.time}</span>
                <span style={{
                  color: line.type === 'dim' ? '#6b5f4e' : line.type === 'tool' ? '#8ba4c4' :
                    line.type === 'success' ? '#7da87e' : line.type === 'accent' ? '#c4a882' : '#b8a88e',
                }}>{line.text}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 1.5rem' }}>

        <hr style={{ border: 'none', borderTop: '1px solid var(--ma-border)', margin: '0 0 3rem' }} />

        {/* How it works — step by step */}
        <section style={{ paddingBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)', marginBottom: '0.35rem' }}>
              How a ticket becomes a deployment
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--ma-muted)' }}>
              From GitHub issue to merged PR — each step handled by a dedicated Claude Code agent.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {PHASES.map((phase, i) => (
              <div key={i} style={{
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
                borderRadius: '0.5rem', overflow: 'hidden',
              }}>
                {/* Phase header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.85rem 1rem', borderBottom: '1px solid var(--ma-border)' }}>
                  <span style={{
                    fontSize: '0.65rem', fontWeight: 600, padding: '0.2rem 0.5rem',
                    borderRadius: '0.25rem', background: 'var(--ma-bg)',
                    border: '1px solid var(--ma-border)', color: phase.color,
                  }}>
                    {phase.status}
                  </span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--ma-fg)' }}>
                    {phase.title}
                  </span>
                </div>
                {/* Phase content */}
                <div style={{ padding: '0.85rem 1rem', display: 'flex', gap: '1.5rem' }}>
                  <p style={{ flex: 1, fontSize: '0.78rem', color: 'var(--ma-muted)', lineHeight: 1.6, margin: 0 }}>
                    {phase.desc}
                  </p>
                  <div style={{
                    flex: '0 0 320px', background: '#1a1612', borderRadius: '0.375rem',
                    padding: '0.5rem 0.65rem', overflow: 'hidden',
                  }}>
                    {phase.log.map((line, j) => (
                      <div key={j} style={{
                        fontSize: '0.62rem', fontFamily: 'var(--ifm-font-family-monospace)',
                        color: line.startsWith('COMMENT') || line.startsWith('REVIEW') ? '#8ba4c4' :
                          line.startsWith('RISK') || line.startsWith('MONITOR') || line.includes('passing') || line.includes('APPROVE') || line.includes('HEALTHY') ? '#7da87e' :
                          line.includes('PR #') || line.includes('Merged') || line.includes('created') ? '#c4a882' :
                          '#a89880',
                        lineHeight: 1.7, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      }}>
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--ma-border)', margin: '0 0 3rem' }} />

        {/* Features */}
        <section style={{ paddingBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)', marginBottom: '1.25rem', textAlign: 'center' }}>
            Built for teams that ship
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            {FEATURES.map(([title, desc]) => (
              <div key={title} style={{
                padding: '1.1rem', background: 'var(--ma-surface)',
                border: '1px solid var(--ma-border)', borderRadius: '0.5rem',
              }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.2rem' }}>{title}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--ma-muted)', lineHeight: 1.5 }}>{desc}</div>
              </div>
            ))}
          </div>
        </section>

        <section style={{ paddingBottom: '4rem', textAlign: 'center' }}>
          <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            {['Python / FastAPI', 'Next.js', 'PostgreSQL', 'Claude Code CLI', 'GitHub', 'Linear'].map((s) => (
              <span key={s} style={{
                fontSize: '0.65rem', padding: '0.2rem 0.55rem', borderRadius: 9999,
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
              }}>{s}</span>
            ))}
          </div>
        </section>

      </div>
    </Layout>
  );
}
