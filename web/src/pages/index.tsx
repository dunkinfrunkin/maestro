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
        setTimeout(() => {
          setStep((step + 1) % HERO_STEPS.length);
          setLineIndex(0);
          setTransitioning(false);
        }, 1200);
      }
    }, isCustom ? 5000 : lineIndex === 0 ? 2000 : 1500);

    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [step, lineIndex, transitioning]);

  return (
    <div style={{
      position: 'relative', width: 680, flexShrink: 0,
    }}>
      {/* Maestro mascot — top right, flipped */}
      <div style={{
        position: 'absolute', top: -36, right: -24, zIndex: 2,
      }}>
        <img
          src="/img/logo.png" alt=""
          style={{ width: 80, height: 80, transform: 'scaleX(-1)' }}
        />
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
              onClick={() => { setStep(i); setLineIndex(0); setTransitioning(false);}}
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

/* ── Landing page data ── */

const STATS = [
  { value: '5', label: 'Dedicated agents' },
  { value: '7', label: 'Risk dimensions' },
  { value: '15m', label: 'Post-deploy monitoring' },
  { value: '0', label: 'Lines of code you write' },
];

const VALUE_PROPS = [
  {
    label: 'From ticket to PR',
    title: 'Your backlog, on autopilot',
    desc: 'Point Maestro at your GitHub or Linear issues. The Implementation Agent clones the repo, reads the codebase, writes the code, runs tests, and opens a pull request. You review the output, not the process.',
  },
  {
    label: 'Agent-to-agent review',
    title: 'Code review that never sleeps',
    desc: 'The Review Agent checks out every PR, reads every changed file, and posts inline comments on specific lines — just like a human reviewer. When fixes land, it verifies, resolves threads, and approves. No context switching required.',
  },
  {
    label: 'Risk scoring',
    title: 'Ship fast without the fear',
    desc: 'Every PR is scored across seven dimensions before it can merge: scope, blast radius, complexity, test coverage, security, reversibility, and dependencies. Low-risk changes auto-approve. High-risk changes escalate to a human.',
  },
  {
    label: 'Post-deploy observability',
    title: 'Confidence after the merge',
    desc: 'The Monitor Agent checks Datadog and Splunk for 15 minutes after every deploy. Latency spikes, error rate changes, new exceptions — all caught automatically. Deploy confidence from verification, not hope.',
  },
];

const PIPELINE_STAGES = [
  { name: 'Implement', color: '#2563eb', desc: 'Clone, read, edit, test, open PR', icon: 'M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5' },
  { name: 'Review', color: '#d97706', desc: 'Inline comments, thread conversations', icon: 'M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z' },
  { name: 'Risk', color: '#7c3aed', desc: '7-dimension scoring, auto-approve', icon: 'M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z' },
  { name: 'Deploy', color: '#059669', desc: 'CI checks, squash merge', icon: 'M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5' },
  { name: 'Monitor', color: '#0891b2', desc: 'Datadog, Splunk, 15-min watch', icon: 'M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6' },
];

const CAPABILITIES = [
  { title: 'Configurable agents', desc: 'Own system prompt, model, and settings per agent. Edit prompts directly in the dashboard.' },
  { title: 'GitHub and Linear', desc: 'Pull issues from either tracker. Encrypted tokens. Filter by repo, label, or project.' },
  { title: 'Plugin framework', desc: 'Build custom agents by subclassing AgentPlugin. Python entry points or drop-in files.' },
  { title: 'Live activity streaming', desc: 'Watch agents work in real time. Every tool call, every edit, streamed as it happens.' },
  { title: 'Workspace isolation', desc: 'Isolated credentials, agent configs, and pipeline settings per project. Teams don\'t collide.' },
  { title: 'Powered by Claude Code', desc: 'Each agent runs as a Claude Code CLI subprocess with full tool access.' },
];

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

      {/* ── Stats bar ── */}
      <section style={{ borderTop: '1px solid var(--ma-border)', borderBottom: '1px solid var(--ma-border)' }}>
        <div style={{
          maxWidth: 1100, margin: '0 auto', padding: '2rem 3rem',
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '2rem',
        }}>
          {STATS.map((s) => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: '2rem', fontWeight: 800, color: 'var(--ma-fg)',
                fontFamily: "'DM Sans', sans-serif", letterSpacing: '-0.03em',
              }}>{s.value}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--ma-muted)', marginTop: '0.15rem' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Value props — alternating left/right ── */}
      <section style={{ maxWidth: 1000, margin: '0 auto', padding: '5rem 3rem' }}>
        {VALUE_PROPS.map((v, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'flex-start', gap: '4rem',
            marginBottom: i < VALUE_PROPS.length - 1 ? '4.5rem' : 0,
            flexDirection: i % 2 === 0 ? 'row' : 'row-reverse',
          }}>
            {/* Text side */}
            <div style={{ flex: '1 1 55%' }}>
              <div style={{
                fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '0.5rem',
              }}>{v.label}</div>
              <h2 style={{
                fontSize: 'clamp(1.5rem, 3vw, 1.9rem)', fontWeight: 800, letterSpacing: '-0.03em',
                fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
                margin: '0 0 0.75rem', lineHeight: 1.15,
              }}>{v.title}</h2>
              <p style={{ fontSize: '0.95rem', color: 'var(--ma-muted)', lineHeight: 1.75, margin: 0 }}>{v.desc}</p>
            </div>
            {/* Visual side — pipeline stage card */}
            <div style={{
              flex: '0 0 280px', padding: '1.5rem', borderRadius: '0.75rem',
              background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
            }}>
              {i === 0 && (
                <div style={{ fontSize: '0.78rem', color: 'var(--ma-fg)', lineHeight: 1.8, fontFamily: 'var(--ifm-font-family-monospace)' }}>
                  <div style={{ color: 'var(--ma-muted)' }}>Cloning repo...</div>
                  <div style={{ color: '#5c7cba' }}>Reading stripe.ts</div>
                  <div style={{ color: '#5c7cba' }}>Editing payments.ts</div>
                  <div style={{ color: '#5c7cba' }}>Running npm test</div>
                  <div style={{ color: '#16a34a', fontWeight: 500, marginTop: '0.25rem' }}>8 passed. PR #142 created.</div>
                </div>
              )}
              {i === 1 && (
                <div style={{ fontSize: '0.78rem', color: 'var(--ma-fg)', lineHeight: 1.8, fontFamily: 'var(--ifm-font-family-monospace)' }}>
                  <div style={{ color: '#5c7cba' }}>Reading changed files...</div>
                  <div style={{ color: '#d97706' }}>stripe.ts:47 — missing key</div>
                  <div style={{ color: 'var(--ma-muted)', marginTop: '0.5rem' }}>--- after fix ---</div>
                  <div style={{ color: '#16a34a' }}>Verified. Thread resolved.</div>
                  <div style={{ color: '#16a34a', fontWeight: 500 }}>Approved.</div>
                </div>
              )}
              {i === 2 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {[
                    ['Scope', 2], ['Blast radius', 2], ['Complexity', 1],
                    ['Coverage', 1], ['Security', 2],
                  ].map(([label, score]) => (
                    <div key={label as string} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--ma-muted)', width: 80, flexShrink: 0 }}>{label}</span>
                      <div style={{ flex: 1, display: 'flex', gap: '0.15rem' }}>
                        {[1,2,3,4,5].map((n) => (
                          <div key={n} style={{
                            flex: 1, height: 5, borderRadius: 2,
                            background: n <= (score as number) ? '#22c55e' : 'var(--ma-border)',
                            opacity: n <= (score as number) ? 1 : 0.3,
                          }} />
                        ))}
                      </div>
                      <span style={{ fontSize: '0.6rem', color: 'var(--ma-muted)', width: 20, textAlign: 'right' }}>{score}/5</span>
                    </div>
                  ))}
                  <div style={{
                    marginTop: '0.5rem', padding: '0.4rem 0.6rem', borderRadius: '0.35rem',
                    background: '#dcfce7', textAlign: 'center',
                    fontSize: '0.72rem', fontWeight: 600, color: '#15803d',
                  }}>LOW — auto-approved</div>
                </div>
              )}
              {i === 3 && (
                <div style={{ fontSize: '0.78rem', color: 'var(--ma-fg)', lineHeight: 1.8, fontFamily: 'var(--ifm-font-family-monospace)' }}>
                  <div style={{ color: 'var(--ma-muted)' }}>Monitoring for 15m...</div>
                  <div style={{ color: '#5c7cba' }}>Checking Datadog...</div>
                  <div style={{ color: 'var(--ma-fg)' }}>Latency: 42ms p99</div>
                  <div style={{ color: '#16a34a' }}>Error rate: 0.00%</div>
                  <div style={{ color: '#5c7cba' }}>Checking Splunk...</div>
                  <div style={{ color: '#16a34a', fontWeight: 500 }}>All systems healthy.</div>
                </div>
              )}
            </div>
          </div>
        ))}
      </section>

      {/* ── Pipeline visualization ── */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 3rem 4rem', textAlign: 'center' }}>
        <div style={{
          fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '0.5rem',
        }}>How it works</div>
        <h2 style={{
          fontSize: 'clamp(1.5rem, 3vw, 1.9rem)', fontWeight: 800, letterSpacing: '-0.03em',
          fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
          margin: '0 0 0.5rem', lineHeight: 1.15,
        }}>
          Five agents. One continuous flow.
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--ma-muted)', lineHeight: 1.7, maxWidth: 480, margin: '0 auto 2.5rem' }}>
          Every ticket moves through the same pipeline. Each agent hands off to the next. Humans intervene only when risk demands it.
        </p>

        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0',
        }}>
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '1.25rem 1.5rem', borderRadius: '0.65rem',
                background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
                textAlign: 'center', minWidth: 140,
              }}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke={stage.color} style={{ width: 28, height: 28, margin: '0 auto 0.5rem', display: 'block' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={stage.icon} />
                </svg>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.2rem' }}>{stage.name}</div>
                <div style={{ fontSize: '0.65rem', color: 'var(--ma-muted)', lineHeight: 1.5 }}>{stage.desc}</div>
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <div style={{ width: 32, display: 'flex', justifyContent: 'center' }}>
                  <span style={{ color: 'var(--ma-muted)', fontSize: '0.65rem' }}>&rarr;</span>
                </div>
              )}
            </div>
          ))}
        </div>

      </section>

      {/* ── Philosophy callout ── */}
      <section style={{ maxWidth: 680, margin: '0 auto', padding: '4rem 2rem', textAlign: 'center' }}>
        <h2 style={{
          fontSize: 'clamp(1.4rem, 3vw, 1.8rem)', fontWeight: 800, letterSpacing: '-0.03em',
          fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
          margin: '0 0 0.75rem', lineHeight: 1.2,
        }}>
          "Humans steer. Agents execute."
        </h2>
        <p style={{ fontSize: '0.92rem', color: 'var(--ma-muted)', lineHeight: 1.7, margin: '0 0 1.25rem' }}>
          When agents handle the software lifecycle, the engineer's job shifts from writing code to designing systems where agents can do reliable work.
        </p>
        <Link to="/philosophy" style={{
          fontSize: '0.85rem', color: 'var(--ma-accent)', fontWeight: 500, textDecoration: 'none',
        }}>Read the full philosophy &rarr;</Link>
      </section>

      {/* ── Capabilities grid ── */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 3rem 4rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '0.5rem',
          }}>Platform</div>
          <h2 style={{
            fontSize: 'clamp(1.5rem, 3vw, 1.9rem)', fontWeight: 800, letterSpacing: '-0.03em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: 0, lineHeight: 1.15,
          }}>
            Everything you need to ship
          </h2>
        </div>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1px', background: 'var(--ma-border)', borderRadius: '0.75rem', overflow: 'hidden',
        }}>
          {CAPABILITIES.map((c) => (
            <div key={c.title} style={{ padding: '1.75rem', background: 'var(--ma-bg)' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.4rem' }}>{c.title}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', lineHeight: 1.65 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section style={{
        maxWidth: 800, margin: '0 auto', padding: '3rem 2rem 5rem', textAlign: 'center',
      }}>
        <h2 style={{
          fontSize: 'clamp(1.6rem, 3.5vw, 2.2rem)', fontWeight: 800, letterSpacing: '-0.03em',
          fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
          margin: '0 0 0.75rem', lineHeight: 1.15,
        }}>
          Stop writing code.<br />Start orchestrating it.
        </h2>
        <p style={{ fontSize: '0.95rem', color: 'var(--ma-muted)', lineHeight: 1.7, margin: '0 0 2rem' }}>
          Open source. Self-hosted. Deploy in minutes.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginBottom: '1.5rem' }}>
          <Link to="/docs/getting-started" style={{
            padding: '0.85rem 2rem', fontSize: '0.95rem', borderRadius: '0.5rem',
            background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 600, textDecoration: 'none',
          }}>Get started</Link>
          <Link to="https://github.com/dunkinfrunkin/maestro" style={{
            padding: '0.85rem 2rem', fontSize: '0.95rem', borderRadius: '0.5rem',
            background: 'transparent', color: 'var(--ma-fg)', fontWeight: 500,
            border: '1px solid var(--ma-border)', textDecoration: 'none',
          }}>View on GitHub</Link>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          {['Python / FastAPI', 'Next.js', 'PostgreSQL', 'Claude Code CLI', 'GitHub', 'Linear'].map((s) => (
            <span key={s} style={{
              fontSize: '0.6rem', padding: '0.2rem 0.5rem', borderRadius: 9999,
              background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
            }}>{s}</span>
          ))}
        </div>
      </section>
    </Layout>
  );
}
