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

/* ── Philosophy sections data ── */

const PRINCIPLES = [
  {
    title: 'Humans steer. Agents execute.',
    desc: 'Engineers define intent, set constraints, and review outcomes. Agents handle the implementation, review, testing, and deployment. The bottleneck shifts from writing code to designing environments where agents can do reliable work.',
  },
  {
    title: 'Every agent gets its own role.',
    desc: 'A single monolithic agent can\'t hold the full context of implementation, review, risk assessment, and deployment. Maestro decomposes the pipeline into dedicated agents, each with a focused system prompt, clear inputs, and a single responsibility.',
  },
  {
    title: 'Agents talk through the same tools humans use.',
    desc: 'Review comments, PR threads, CI checks, GitHub API calls. Agents don\'t use special channels. They post inline comments on specific lines of code, reply in threads, resolve conversations, and approve pull requests — the same workflow as human developers.',
  },
  {
    title: 'Corrections are cheap. Waiting is expensive.',
    desc: 'In high-throughput agent systems, the cost of a follow-up fix is almost always lower than the cost of blocking progress. Maestro favors fast iteration over gated perfection — review agents catch issues, implementation agents fix them, and the loop continues.',
  },
  {
    title: 'Risk is scored, not assumed.',
    desc: 'Not every change needs a human in the loop. Maestro scores each PR across seven dimensions — scope, blast radius, complexity, test coverage, security, reversibility, and dependencies. Low-risk changes auto-approve. High-risk changes escalate.',
  },
  {
    title: 'Observability is not optional.',
    desc: 'After merge, a monitor agent checks Datadog dashboards and Splunk logs for 15 minutes. If latency spikes or error rates climb, it flags the change. Deploy confidence comes from automated post-deploy verification, not hope.',
  },
];

const PIPELINE_STAGES = [
  { name: 'Implement', color: '#2563eb', desc: 'Clone, read, edit, test, open PR' },
  { name: 'Review', color: '#d97706', desc: 'Inline comments, thread conversations' },
  { name: 'Risk', color: '#7c3aed', desc: '7-dimension scoring, auto-approve threshold' },
  { name: 'Deploy', color: '#059669', desc: 'CI verification, squash merge' },
  { name: 'Monitor', color: '#0891b2', desc: 'Datadog, Splunk, 15-minute health check' },
];

const CAPABILITIES = [
  { title: 'Configurable agents', desc: 'Each agent has its own system prompt, model, and settings. Edit prompts directly in the dashboard. Swap models per agent.' },
  { title: 'GitHub and Linear', desc: 'Pull issues from either tracker. Connections stored with encrypted tokens. Filter by repo, label, or project.' },
  { title: 'Plugin framework', desc: 'Build custom agents by subclassing AgentPlugin. Register via Python entry points or drop files in a plugins directory.' },
  { title: 'Live activity streaming', desc: 'Watch agents work in real time. Every tool call, every edit, every decision — streamed to the dashboard as it happens.' },
  { title: 'Workspace isolation', desc: 'Each project gets its own workspace with isolated credentials, agent configs, and pipeline settings. Teams don\'t collide.' },
  { title: 'Powered by Claude Code', desc: 'Each agent runs as a Claude Code CLI subprocess with full access to Read, Write, Edit, Bash, Glob, and Grep.' },
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

      {/* ── Section: Philosophy ── */}
      <section style={{ maxWidth: 900, margin: '0 auto', padding: '5rem 3rem 1rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
          <div style={{
            fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '0.75rem',
          }}>
            Philosophy
          </div>
          <h2 style={{
            fontSize: 'clamp(1.8rem, 3.5vw, 2.4rem)', fontWeight: 800, letterSpacing: '-0.03em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: '0 0 1rem', lineHeight: 1.15,
          }}>
            Harness engineering for the<br />agent-first world
          </h2>
          <p style={{ fontSize: '1rem', color: 'var(--ma-muted)', lineHeight: 1.7, maxWidth: 600, margin: '0 auto' }}>
            When agents handle the software lifecycle, the engineer's job shifts from writing code to designing systems where agents can do reliable work. Maestro encodes that philosophy into a pipeline.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {PRINCIPLES.map((p, i) => (
            <div key={i} style={{
              padding: '1.75rem 0',
              borderTop: '1px solid var(--ma-border)',
            }}>
              <div style={{
                fontSize: '1.05rem', fontWeight: 700, color: 'var(--ma-fg)',
                marginBottom: '0.5rem', lineHeight: 1.3,
              }}>
                {p.title}
              </div>
              <div style={{ fontSize: '0.88rem', color: 'var(--ma-muted)', lineHeight: 1.7 }}>
                {p.desc}
              </div>
            </div>
          ))}
        </div>

        <div style={{ paddingTop: '1.5rem', borderTop: '1px solid var(--ma-border)' }}>
          <Link to="/philosophy" style={{
            fontSize: '0.85rem', color: 'var(--ma-accent)', fontWeight: 500, textDecoration: 'none',
          }}>Read the full philosophy &rarr;</Link>
        </div>
      </section>

      {/* ── Section: The Pipeline (visual) ── */}
      <section style={{ padding: '4rem 3rem', background: '#1a1612' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <div style={{
              fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: '0.1em', color: '#706555', marginBottom: '0.75rem',
            }}>
              The Pipeline
            </div>
            <h2 style={{
              fontSize: 'clamp(1.6rem, 3vw, 2rem)', fontWeight: 800, letterSpacing: '-0.03em',
              fontFamily: "'DM Sans', sans-serif", color: '#e8e0d4',
              margin: '0 0 0.75rem', lineHeight: 1.15,
            }}>
              Five agents. One continuous flow.
            </h2>
            <p style={{ fontSize: '0.9rem', color: '#a89880', lineHeight: 1.7, maxWidth: 520, margin: '0 auto' }}>
              Every ticket moves through the same pipeline. Each agent hands off to the next. Humans intervene only when risk demands it.
            </p>
          </div>

          {/* Pipeline flow visualization */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '0', flexWrap: 'nowrap',
          }}>
            {PIPELINE_STAGES.map((stage, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{
                  padding: '1.25rem 1.5rem', borderRadius: '0.65rem',
                  background: '#242018', border: `1px solid ${stage.color}30`,
                  textAlign: 'center', minWidth: 150,
                }}>
                  <div style={{
                    width: 10, height: 10, borderRadius: '50%',
                    background: stage.color, margin: '0 auto 0.6rem',
                    boxShadow: `0 0 12px ${stage.color}50`,
                  }} />
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#e8e0d4', marginBottom: '0.3rem' }}>
                    {stage.name}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#706555', lineHeight: 1.5 }}>
                    {stage.desc}
                  </div>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div style={{
                    width: 40, height: 1, background: '#3d3428', position: 'relative',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <span style={{ color: '#706555', fontSize: '0.7rem' }}>&rarr;</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* CLI line */}
          <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
            <code style={{ fontSize: '0.72rem', color: '#706555', fontFamily: 'var(--ifm-font-family-monospace)' }}>
              $ claude -p "..." --model claude-sonnet-4-6 --output-format stream-json
            </code>
          </div>
        </div>
      </section>

      {/* ── Section: Capabilities ── */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '4rem 3rem 3rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '0.75rem',
          }}>
            Capabilities
          </div>
          <h2 style={{
            fontSize: 'clamp(1.6rem, 3vw, 2rem)', fontWeight: 800, letterSpacing: '-0.03em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: 0, lineHeight: 1.15,
          }}>
            Built for teams that ship
          </h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1px', background: 'var(--ma-border)', borderRadius: '0.75rem', overflow: 'hidden' }}>
          {CAPABILITIES.map((c) => (
            <div key={c.title} style={{ padding: '1.75rem', background: 'var(--ma-bg)' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.4rem' }}>{c.title}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', lineHeight: 1.65 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section style={{ maxWidth: 640, margin: '0 auto', padding: '2rem 1.5rem 5rem', textAlign: 'center' }}>
        <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
          {['Python / FastAPI', 'Next.js', 'PostgreSQL', 'Claude Code CLI', 'GitHub', 'Linear'].map((s) => (
            <span key={s} style={{
              fontSize: '0.65rem', padding: '0.2rem 0.55rem', borderRadius: 9999,
              background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
            }}>{s}</span>
          ))}
        </div>
        <Link to="/docs/getting-started" style={{
          padding: '0.75rem 1.75rem', fontSize: '0.9rem', borderRadius: '0.5rem',
          background: 'var(--ma-accent)', color: '#f5f0e8', fontWeight: 600, textDecoration: 'none',
        }}>Get started</Link>
      </section>
    </Layout>
  );
}
