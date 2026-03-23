import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

const PIPELINE = [
  { name: 'Queued', desc: 'Ready for work' },
  { name: 'Implement', desc: 'Write code' },
  { name: 'Review', desc: 'Post comments' },
  { name: 'Risk Profile', desc: 'Score risk' },
  { name: 'Deploy', desc: 'Merge + CI' },
  { name: 'Monitor', desc: 'Health check' },
];

const TIMELINE = [
  { agent: 'Implementation Agent', content: 'Reading src/books.js, src/router.js. Adding searchBooks function and GET /books/search route. Running tests — 6 passed. Creating PR #24.' },
  { agent: 'Review Agent', content: 'src/books.test.js:31 — Test named "returns multiple matches" but asserts length === 1. Misleading.' },
  { agent: 'Implementation Agent', content: 'Fixed: Changed query to "an" which matches 2 books. Assertion updated to length === 2.' },
  { agent: 'Review Agent', content: 'Verified — fix looks good. All threads resolved. APPROVE.' },
  { agent: 'Risk Profile Agent', content: 'Change Scope: 1/5. Blast Radius: 1/5. Complexity: 1/5. Overall: LOW. Auto-approved.' },
  { agent: 'Deployment Agent', content: 'CI checks passing. Merged via squash. Deployment complete.' },
];

const FEATURES = [
  { title: 'Multi-agent pipeline', desc: 'Five agents work in sequence — implement, review, risk-assess, deploy, and monitor. Each handles one responsibility.' },
  { title: 'Inline PR code reviews', desc: 'Review agent posts comments on specific lines of code. Implementation agent replies in the thread with fixes.' },
  { title: 'Comment thread conversations', desc: 'Agents chat back and forth in PR threads, resolving issues just like human developers would.' },
  { title: 'Configurable prompts and models', desc: 'Each agent has its own system prompt and model selection. Edit prompts directly in the dashboard.' },
  { title: 'GitHub and Linear integrations', desc: 'Pull tasks from GitHub Issues or Linear. Encrypted token storage. Access all repos or filter to specific ones.' },
  { title: 'Plugin framework', desc: 'Build custom agents by subclassing AgentPlugin. Register via entry points or a plugins directory.' },
];

export default function Home() {
  return (
    <Layout title="Maestro" description="Autonomous coding agent orchestration for enterprise teams">
      {/* Hero */}
      <section style={{ padding: '6rem 2rem 3rem', textAlign: 'center', maxWidth: 800, margin: '0 auto' }}>
        <div style={{
          display: 'inline-block', fontSize: '0.75rem', padding: '0.35rem 0.75rem',
          borderRadius: 9999, background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
          color: 'var(--ma-muted)', marginBottom: '1.5rem'
        }}>
          <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#b8860b', marginRight: '0.5rem', verticalAlign: 'middle' }} />
          Under active development
        </div>
        <h1 style={{ fontSize: '3.5rem', fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--ma-foreground)', marginBottom: '0.5rem' }}>
          Maestro
        </h1>
        <p style={{ fontSize: '1.15rem', color: 'var(--ma-muted)', marginBottom: '2rem', lineHeight: 1.6 }}>
          Autonomous coding agent orchestration for enterprise teams.
          <br />
          Inspired by <a href="https://github.com/openai/symphony" style={{ color: 'var(--ma-accent)' }}>Symphony</a>, built for production.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          <Link to="/docs/getting-started" style={{
            padding: '0.6rem 1.5rem', fontSize: '0.875rem', borderRadius: '0.375rem',
            background: 'var(--ma-accent)', color: 'var(--ma-bg)', fontWeight: 500, textDecoration: 'none',
          }}>
            Get Started
          </Link>
          <Link to="https://github.com/dunkinfrunkin/maestro" style={{
            padding: '0.6rem 1.5rem', fontSize: '0.875rem', borderRadius: '0.375rem',
            background: 'var(--ma-surface)', color: 'var(--ma-foreground)', fontWeight: 500,
            border: '1px solid var(--ma-border)', textDecoration: 'none',
          }}>
            GitHub
          </Link>
        </div>
      </section>

      {/* Pipeline */}
      <section style={{ padding: '2rem 2rem 3rem', maxWidth: 900, margin: '0 auto' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--ma-foreground)', marginBottom: '0.25rem', textAlign: 'center' }}>
          Harness Engineering Pipeline
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', textAlign: 'center', marginBottom: '1.5rem' }}>
          Each stage is handled by a dedicated AI agent. Review loops until all comments are resolved.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 0 }}>
          {PIPELINE.map((step, i) => (
            <div key={step.name} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ textAlign: 'center', padding: '0.75rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ma-foreground)' }}>{step.name}</div>
                <div style={{ fontSize: '0.6rem', color: 'var(--ma-muted)' }}>{step.desc}</div>
              </div>
              {i < PIPELINE.length - 1 && (
                <span style={{ color: 'var(--ma-border)', fontSize: '1rem', margin: '0 0.15rem' }}>
                  {i === 2 ? '< >' : '>'}
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Example run */}
      <section style={{ padding: '2rem 2rem 3rem', maxWidth: 700, margin: '0 auto' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--ma-foreground)', marginBottom: '0.25rem' }}>
          Example: Adding a search endpoint
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--ma-muted)', marginBottom: '1.5rem' }}>
          A task moves through each pipeline stage automatically.
        </p>
        <div style={{ borderLeft: '2px solid var(--ma-border)', paddingLeft: '1.25rem', marginLeft: '0.5rem' }}>
          {TIMELINE.map((entry, i) => (
            <div key={i} style={{ marginBottom: '1.25rem', position: 'relative' }}>
              <div style={{
                position: 'absolute', left: '-1.6rem', top: '0.35rem',
                width: 8, height: 8, borderRadius: '50%', background: 'var(--ma-accent)',
              }} />
              <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--ma-foreground)', marginBottom: '0.2rem' }}>
                {entry.agent}
              </div>
              <div style={{
                fontSize: '0.75rem', color: 'var(--ma-muted)', background: 'var(--ma-surface)',
                border: '1px solid var(--ma-border)', borderRadius: '0.375rem',
                padding: '0.5rem 0.75rem', fontFamily: 'var(--ifm-font-family-monospace)', lineHeight: 1.5,
              }}>
                {entry.content}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section style={{ padding: '2rem 2rem 3rem', maxWidth: 900, margin: '0 auto' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--ma-foreground)', marginBottom: '1.5rem', textAlign: 'center' }}>
          Features
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          {FEATURES.map((f) => (
            <div key={f.title} style={{
              padding: '1.25rem', background: 'var(--ma-surface)',
              border: '1px solid var(--ma-border)', borderRadius: '0.5rem',
            }}>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--ma-foreground)', marginBottom: '0.25rem' }}>
                {f.title}
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--ma-muted)', margin: 0, lineHeight: 1.5 }}>
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Stack */}
      <section style={{ padding: '1rem 2rem 4rem', maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          {['Python / FastAPI', 'Next.js', 'PostgreSQL', 'Claude Code CLI', 'GitHub Issues', 'Linear'].map((s) => (
            <span key={s} style={{
              fontSize: '0.7rem', padding: '0.25rem 0.6rem', borderRadius: 9999,
              background: 'var(--ma-surface)', border: '1px solid var(--ma-border)', color: 'var(--ma-muted)',
            }}>
              {s}
            </span>
          ))}
        </div>
      </section>
    </Layout>
  );
}
