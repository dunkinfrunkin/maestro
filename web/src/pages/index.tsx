import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

const PHASES = [
  {
    title: 'A ticket enters the pipeline',
    desc: 'A team member files a GitHub issue. Maestro syncs it to a workspace and queues it for the implementation agent.',
    agent: null,
    log: ['GitHub Issue #47: Add POST /payments/refund endpoint', 'Status set to: Queued'],
  },
  {
    title: 'The implementation agent writes code',
    desc: 'Claude Code clones the repo, reads the codebase, writes the implementation, runs tests, and opens a pull request — all autonomously.',
    agent: { name: 'Implementation Agent', status: 'completed', statusColor: '#16a34a', statusBg: '#dcfce7', statusBorder: '#bbf7d0' },
    log: [
      { type: 'status', text: 'Cloning acme/payments-api' },
      { type: 'tool', text: 'Using tool: Read — src/services/stripe.ts' },
      { type: 'tool', text: 'Using tool: Edit — src/routes/payments.ts' },
      { type: 'tool', text: 'Using tool: Bash — npm test' },
      { type: 'text', text: 'Tests: 8 passed. Creating PR #142.' },
      { type: 'status', text: 'PR created: acme/payments-api/pull/142' },
    ],
  },
  {
    title: 'Code review with inline comments',
    desc: 'The review agent checks out the PR, reads every changed file, and posts inline comments on specific lines — exactly like a human reviewer.',
    agent: { name: 'Review Agent', status: 'completed', statusColor: '#16a34a', statusBg: '#dcfce7', statusBorder: '#bbf7d0' },
    log: [
      { type: 'tool', text: 'Using tool: Bash — gh pr checkout 142' },
      { type: 'tool', text: 'Using tool: Read — src/services/stripe.ts' },
      { type: 'text', text: 'stripe.ts:47 — missing idempotency key for refund' },
      { type: 'text', text: 'REVIEW_VERDICT: REQUEST_CHANGES' },
    ],
  },
  {
    title: 'Fixes committed, replied in thread',
    desc: 'The implementation agent reads each review comment, makes the fix, and replies directly in the PR comment thread — the same workflow as human developers.',
    agent: { name: 'Implementation Agent', status: 'completed', statusColor: '#16a34a', statusBg: '#dcfce7', statusBorder: '#bbf7d0' },
    log: [
      { type: 'tool', text: 'Using tool: Read — comment #2970403242' },
      { type: 'tool', text: 'Using tool: Edit — src/services/stripe.ts' },
      { type: 'text', text: 'Fixed: added idempotency_key parameter' },
      { type: 'tool', text: 'Using tool: Bash — git push' },
      { type: 'status', text: 'Replied to comment thread' },
    ],
  },
  {
    title: 'Verified, resolved, approved',
    desc: 'The review agent checks each comment, verifies the fix in the code, replies with confirmation, resolves the thread, and approves.',
    agent: { name: 'Review Agent', status: 'completed', statusColor: '#16a34a', statusBg: '#dcfce7', statusBorder: '#bbf7d0' },
    log: [
      { type: 'text', text: 'Verified — fix looks good.' },
      { type: 'status', text: 'Thread resolved via GraphQL' },
      { type: 'text', text: 'REVIEW_VERDICT: APPROVE' },
    ],
  },
  {
    title: 'Risk scored and auto-approved',
    desc: 'The risk agent scores the PR across seven dimensions. Low-risk changes are auto-approved. Medium and above require human review.',
    agent: { name: 'Risk Profile Agent', status: 'completed', statusColor: '#16a34a', statusBg: '#dcfce7', statusBorder: '#bbf7d0' },
    log: [
      { type: 'text', text: 'Scope 2/5 | Blast 2/5 | Complexity 1/5' },
      { type: 'text', text: 'Test Coverage 1/5 | Security 2/5' },
      { type: 'status', text: 'RISK_LEVEL: LOW — auto-approved' },
    ],
  },
  {
    title: 'Merged and deployed',
    desc: 'The deployment agent verifies CI, merges via squash, and monitors the pipeline. The monitor agent checks post-deploy health.',
    agent: { name: 'Deployment Agent', status: 'completed', statusColor: '#16a34a', statusBg: '#dcfce7', statusBorder: '#bbf7d0' },
    log: [
      { type: 'tool', text: 'Using tool: Bash — gh pr merge --squash' },
      { type: 'status', text: 'CI: 4/4 passing. Merged.' },
      { type: 'status', text: 'MONITOR_STATUS: HEALTHY' },
    ],
  },
];

const FEATURES = [
  ['Autonomous pipeline', 'Tickets flow through implement, review, risk, deploy, and monitor — each handled by a dedicated Claude Code agent.'],
  ['PR conversations', 'Agents post inline comments and reply in threads. Review resolves conversations via GitHub API when fixes are verified.'],
  ['Risk scoring', 'Seven-dimension risk assessment before every deploy. Configurable auto-approve threshold per workspace.'],
  ['Configurable agents', 'Each agent has its own system prompt, model selection, and settings. Edit prompts directly in the dashboard.'],
  ['GitHub and Linear', 'Pull issues from either tracker. Connections stored with encrypted tokens. Access all repos or filter specific ones.'],
  ['Plugin framework', 'Build custom agents by subclassing AgentPlugin. Register via Python entry points or drop files in a plugins directory.'],
];

function AgentCard({ phase }: { phase: typeof PHASES[0] }) {
  const a = phase.agent;
  return (
    <div style={{
      background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
      borderRadius: '0.5rem', overflow: 'hidden', width: '100%',
    }}>
      {/* Header — matches platform RunEntry */}
      {a && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.6rem 0.75rem', borderBottom: '1px solid var(--ma-border)',
        }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: a.statusColor, flexShrink: 0 }} />
          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--ma-fg)' }}>{a.name}</span>
          <span style={{
            fontSize: '0.58rem', padding: '0.12rem 0.4rem', borderRadius: 9999,
            background: a.statusBg, color: a.statusColor, border: `1px solid ${a.statusBorder}`,
            fontWeight: 500,
          }}>
            {a.status}
          </span>
        </div>
      )}
      {/* Log — matches platform log viewer */}
      <div style={{
        padding: '0.5rem 0', background: a ? 'var(--ma-bg)' : 'var(--ma-surface)',
      }}>
        {phase.log.map((line, j) => {
          const entry = typeof line === 'string' ? { type: 'text', text: line } : line;
          return (
            <div key={j} style={{
              padding: '0.15rem 0.75rem',
              fontSize: '0.68rem',
              fontFamily: 'var(--ifm-font-family-monospace)',
              lineHeight: 1.65,
              color: entry.type === 'tool' ? '#5c7cba' :
                     entry.type === 'status' ? 'var(--ma-muted)' :
                     'var(--ma-fg)',
              fontStyle: entry.type === 'status' ? 'italic' : 'normal',
            }}>
              {entry.text}
            </div>
          );
        })}
      </div>
    </div>
  );
}

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

      {/* Pipeline walkthrough — left description, right agent card */}
      <section style={{ maxWidth: 880, margin: '0 auto', padding: '0 1.5rem 4rem' }}>
        <h2 style={{
          fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
          color: 'var(--ma-fg)', textAlign: 'center', marginBottom: '3rem',
        }}>
          From issue to production
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {PHASES.map((phase, i) => (
            <div key={i} style={{
              display: 'flex', gap: '2.5rem', alignItems: 'flex-start',
              padding: '2rem 0',
              borderBottom: i < PHASES.length - 1 ? '1px solid var(--ma-border)' : 'none',
            }}>
              {/* Left: description */}
              <div style={{ flex: '0 0 300px', paddingTop: '0.5rem' }}>
                <div style={{
                  fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
                  letterSpacing: '0.06em', color: 'var(--ma-muted)', marginBottom: '0.4rem',
                }}>
                  Step {i + 1}
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.4rem', lineHeight: 1.3 }}>
                  {phase.title}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', lineHeight: 1.6 }}>
                  {phase.desc}
                </div>
              </div>
              {/* Right: agent card */}
              <div style={{ flex: 1 }}>
                <AgentCard phase={phase} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Dark break */}
      <section style={{ background: '#1a1612', padding: '3.5rem 1.5rem' }}>
        <div style={{ maxWidth: 640, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif", color: '#e8e0d4', margin: '0 0 0.5rem' }}>
            Powered by Claude Code
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#a89880', lineHeight: 1.6, margin: '0 0 1.5rem' }}>
            Each agent runs as a Claude Code CLI subprocess with full access to
            Read, Write, Edit, Bash, Glob, and Grep.
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
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.3rem' }}>{title}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--ma-muted)', lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
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
