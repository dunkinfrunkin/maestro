import { useState, useEffect, useRef } from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

/* ── Hero animation: pipeline steps that auto-cycle ── */

const HERO_STEPS = [
  {
    agent: 'Implementation Agent',
    color: '#2563eb',
    lines: [
      { text: 'Cloning acme/payments-api...', style: 'muted' },
      { text: 'Reading src/services/stripe.ts', style: 'tool' },
      { text: 'Editing src/routes/payments.ts', style: 'tool' },
      { text: 'Running npm test', style: 'tool' },
      { text: 'Tests: 8 passed', style: 'success' },
      { text: 'PR #142 created', style: 'success' },
    ],
  },
  {
    agent: 'Review Agent',
    color: '#d97706',
    lines: [
      { text: 'Checking out PR #142...', style: 'muted' },
      { text: 'Reading src/services/stripe.ts', style: 'tool' },
      { text: 'Reading src/routes/payments.ts', style: 'tool' },
      { text: 'No issues found', style: 'success' },
      { text: 'Verdict: Approved', style: 'success' },
    ],
  },
  {
    agent: 'Risk Profile Agent',
    color: '#7c3aed',
    custom: 'risk',
    lines: [],
  },
  {
    agent: 'Deployment Agent',
    color: '#059669',
    lines: [
      { text: 'Checking GitHub Actions pipelines...', style: 'muted' },
      { text: 'CI: build — passed', style: 'success' },
      { text: 'CI: lint — passed', style: 'success' },
      { text: 'CI: test — passed (47 tests)', style: 'success' },
      { text: 'CI: deploy-preview — passed', style: 'success' },
      { text: 'All checks green. Merging via squash...', style: 'muted' },
      { text: 'Merged to main', style: 'success' },
    ],
  },
  {
    agent: 'Monitor Agent',
    color: '#0891b2',
    lines: [
      { text: 'Monitoring for 15 minutes...', style: 'muted' },
      { text: 'Checking Datadog dashboards...', style: 'tool' },
      { text: 'API latency: 42ms p99', style: 'default' },
      { text: 'Error rate: 0.00%', style: 'success' },
      { text: 'Checking Splunk logs...', style: 'tool' },
      { text: 'No new exceptions detected', style: 'success' },
      { text: '15m elapsed — all systems healthy', style: 'success' },
    ],
  },
];

const LINE_COLORS: Record<string, string> = {
  muted: 'var(--ma-muted)',
  tool: '#5c7cba',
  success: '#16a34a',
  warn: '#d97706',
  default: 'var(--ma-fg)',
};

const RISK_DIMS = [
  { label: 'Scope', score: 2 },
  { label: 'Blast Radius', score: 2 },
  { label: 'Complexity', score: 1 },
  { label: 'Test Coverage', score: 1 },
  { label: 'Security', score: 2 },
  { label: 'Reversibility', score: 1 },
  { label: 'Dependencies', score: 1 },
];

function RiskScoreCard() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', animation: 'fadeSlideIn 0.4s ease-out' }}>
      {/* Overall verdict */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0.6rem 0.85rem', borderRadius: '0.5rem',
        background: '#dcfce7', border: '1px solid #bbf7d0',
      }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#15803d' }}>Overall Risk</span>
        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#15803d' }}>LOW</span>
      </div>

      {/* Dimension scores */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {RISK_DIMS.map((d) => (
          <div key={d.label} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--ma-muted)', width: 90, flexShrink: 0 }}>{d.label}</span>
            <div style={{ flex: 1, display: 'flex', gap: '0.2rem' }}>
              {[1, 2, 3, 4, 5].map((n) => (
                <div key={n} style={{
                  flex: 1, height: 6, borderRadius: 2,
                  background: n <= d.score
                    ? d.score <= 2 ? '#22c55e' : d.score <= 3 ? '#eab308' : '#ef4444'
                    : 'var(--ma-border)',
                  opacity: n <= d.score ? 1 : 0.3,
                }} />
              ))}
            </div>
            <span style={{ fontSize: '0.65rem', color: 'var(--ma-muted)', width: 24, textAlign: 'right' }}>{d.score}/5</span>
          </div>
        ))}
      </div>

      {/* Auto-approve note */}
      <div style={{
        fontSize: '0.7rem', color: 'var(--ma-muted)', fontStyle: 'italic',
        paddingTop: '0.25rem', borderTop: '1px solid var(--ma-border)',
      }}>
        Below threshold — auto-approved for merge
      </div>
    </div>
  );
}

function HeroPipelineCard() {
  const [step, setStep] = useState(0);
  const [lineIndex, setLineIndex] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const [sparkles, setSparkles] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const current = HERO_STEPS[step];

  useEffect(() => {
    if (transitioning) return;

    const isCustom = !!(current as any).custom;
    const doneWithLines = !isCustom && lineIndex >= current.lines.length - 1;
    const shouldAdvance = isCustom || doneWithLines;

    timerRef.current = setTimeout(() => {
      if (!shouldAdvance) {
        setLineIndex(lineIndex + 1);
      } else {
        // Transition to next step
        setTransitioning(true);
        setSparkles(true);
        setTimeout(() => {
          setStep((step + 1) % HERO_STEPS.length);
          setLineIndex(0);
          setTransitioning(false);
          setTimeout(() => setSparkles(false), 600);
        }, 1200);
      }
    }, isCustom ? 3500 : lineIndex === 0 ? 1400 : 1000);

    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [step, lineIndex, transitioning]);

  return (
    <div style={{
      position: 'relative', width: 680, flexShrink: 0,
    }}>
      {/* Maestro mascot — top right, flipped */}
      <div style={{
        position: 'absolute', top: -36, right: -24, zIndex: 2,
        transition: 'transform 0.4s ease',
        transform: sparkles ? 'scale(1.1)' : 'scale(1)',
      }}>
        <img
          src="/img/logo.png" alt=""
          style={{ width: 80, height: 80, transform: 'scaleX(-1)' }}
        />
        {/* Sparkle particles */}
        {sparkles && (
          <div style={{ position: 'absolute', top: -8, left: -8, right: -8, bottom: -8, pointerEvents: 'none' }}>
            {[...Array(6)].map((_, i) => (
              <span key={i} style={{
                position: 'absolute',
                top: `${20 + Math.sin(i * 1.2) * 30}%`,
                left: `${20 + Math.cos(i * 1.5) * 30}%`,
                width: 4, height: 4, borderRadius: '50%',
                background: i % 2 === 0 ? '#d97706' : '#7c3aed',
                animation: 'sparkle 0.8s ease-out forwards',
                animationDelay: `${i * 0.08}s`,
                opacity: 0,
              }} />
            ))}
          </div>
        )}
      </div>

      {/* Card */}
      <div style={{
        background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
        borderRadius: '0.75rem', overflow: 'hidden',
        boxShadow: '0 20px 50px rgba(0,0,0,0.08)',
        transition: 'border-color 0.4s ease',
        borderColor: transitioning ? current.color : 'var(--ma-border)',
      }}>
        {/* Agent header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.6rem',
          padding: '1.1rem 1.5rem', borderBottom: '1px solid var(--ma-border)',
          transition: 'opacity 0.3s ease',
          opacity: transitioning ? 0 : 1,
        }}>
          <div style={{
            width: 11, height: 11, borderRadius: '50%', flexShrink: 0,
            background: current.color,
            boxShadow: `0 0 8px ${current.color}40`,
          }} />
          <span style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--ma-fg)' }}>
            {current.agent}
          </span>
          <span style={{
            fontSize: '0.6rem', padding: '0.15rem 0.5rem', borderRadius: 9999,
            background: transitioning ? '#dcfce7' : `${current.color}15`,
            color: transitioning ? '#16a34a' : current.color,
            border: `1px solid ${transitioning ? '#bbf7d0' : current.color + '30'}`,
            fontWeight: 500, marginLeft: 'auto',
          }}>
            {transitioning ? 'completed' : 'running'}
          </span>
        </div>

        {/* Log lines — animated in one by one */}
        <div style={{
          padding: '1.25rem 1.5rem', height: 300, overflow: 'hidden',
          background: 'var(--ma-bg)',
          transition: 'opacity 0.3s ease',
          opacity: transitioning ? 0 : 1,
        }}>
          {(current as any).custom === 'risk' ? (
            <RiskScoreCard />
          ) : (
            current.lines.slice(0, lineIndex + 1).map((line, j) => (
              <div key={`${step}-${j}`} style={{
                padding: '0.2rem 0',
                fontSize: '0.95rem',
                lineHeight: 1.7,
                color: LINE_COLORS[line.style] || 'var(--ma-fg)',
                fontWeight: line.style === 'success' ? 500 : 400,
                animation: j === lineIndex ? 'fadeSlideIn 0.3s ease-out' : undefined,
              }}>
                {line.style === 'tool' && (
                  <span style={{ color: 'var(--ma-muted)', marginRight: '0.35rem', fontSize: '0.65rem' }}>&#9656;</span>
                )}
                {line.text}
              </div>
            ))
          )}
        </div>

        {/* Step progress bar + labels — clickable */}
        <div style={{
          display: 'flex', gap: '0.35rem', padding: '0.75rem 1.5rem 0.85rem',
          borderTop: '1px solid var(--ma-border)',
        }}>
          {HERO_STEPS.map((s, i) => (
            <button
              key={i}
              onClick={() => { setStep(i); setLineIndex(0); setTransitioning(false); setSparkles(false); }}
              style={{
                flex: 1, border: 'none', background: 'none', padding: 0, cursor: 'pointer',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem',
              }}
            >
              <div style={{
                width: '100%', height: 5, borderRadius: 3,
                background: i < step ? '#16a34a' : i === step ? current.color : 'var(--ma-border)',
                opacity: i <= step ? 1 : 0.4,
                transition: 'background 0.4s ease, opacity 0.4s ease',
              }} />
              <span style={{
                fontSize: '0.55rem', fontWeight: i === step ? 600 : 400,
                color: i === step ? 'var(--ma-fg)' : 'var(--ma-muted)',
                transition: 'color 0.3s ease',
                whiteSpace: 'nowrap',
              }}>
                {s.agent.replace(' Agent', '')}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

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

      {/* Hero — full-width split: text left, visual right */}
      <section style={{
        display: 'flex', alignItems: 'center', minHeight: 'calc(100vh - 60px)',
        padding: '3rem 4rem', gap: '4rem',
      }}>
        {/* Left: copy */}
        <div style={{ flex: '1 1 50%', maxWidth: 620 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.3rem 0.75rem', borderRadius: 9999, marginBottom: '1.5rem',
            background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#16a34a' }} />
            <span style={{ fontSize: '0.7rem', color: 'var(--ma-muted)', fontWeight: 500 }}>Under active development</span>
          </div>
          <h1 style={{
            fontSize: 'clamp(2.8rem, 5vw, 4rem)', fontWeight: 800, letterSpacing: '-0.04em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: '0 0 1.25rem', lineHeight: 1.05,
          }}>
            Your codebase,<br />orchestrated.
          </h1>
          <p style={{ fontSize: '1.15rem', color: 'var(--ma-muted)', lineHeight: 1.7, margin: '0 0 2rem', maxWidth: 480 }}>
            AI agents that implement, review, and deploy your tickets — from issue to production, autonomously.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <Link to="/docs/getting-started" style={{
              padding: '0.75rem 1.75rem', fontSize: '0.9rem', borderRadius: '0.5rem',
              background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 600, textDecoration: 'none',
            }}>Get started</Link>
            <Link to="https://github.com/dunkinfrunkin/maestro" style={{
              padding: '0.75rem 1.75rem', fontSize: '0.9rem', borderRadius: '0.5rem',
              background: 'transparent', color: 'var(--ma-fg)', fontWeight: 500,
              border: '1px solid var(--ma-border)', textDecoration: 'none',
            }}>View source</Link>
          </div>
        </div>

        {/* Right: animated pipeline simulation card */}
        <div style={{ flex: '1 1 50%', display: 'flex', justifyContent: 'center' }}>
          <HeroPipelineCard />
        </div>
      </section>

      {/* Pipeline walkthrough — left description, right agent card */}
      <section style={{ maxWidth: 1400, margin: '0 auto', padding: '0 3rem 4rem' }}>
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
              <div style={{ flex: '0 0 40%', paddingTop: '0.5rem' }}>
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
      <section style={{ maxWidth: 1400, margin: '0 auto', padding: '4rem 3rem 3rem' }}>
        <h2 style={{
          fontSize: '1.5rem', fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
          color: 'var(--ma-fg)', textAlign: 'center', marginBottom: '2rem',
        }}>
          Built for teams that ship
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
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
