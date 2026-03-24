import Layout from '@theme/Layout';

/* Shared text style to avoid repetition */
const prose = {
  fontSize: '1.05rem', color: 'var(--ma-muted)', lineHeight: 1.85, margin: '0 0 1.25rem',
} as const;

const heading = (text: string) => (
  <h2 style={{
    fontSize: 'clamp(1.5rem, 3vw, 1.9rem)', fontWeight: 800, letterSpacing: '-0.03em',
    fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
    margin: '0 0 1rem', lineHeight: 1.15,
  }}>
    {text}
  </h2>
);

export default function Philosophy() {
  return (
    <Layout title="Philosophy" description="Design principles behind Maestro">

      {/* Hero */}
      <section style={{ maxWidth: 740, margin: '0 auto', padding: '5rem 2rem 3rem' }}>
        <div style={{
          fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '1rem',
        }}>
          Philosophy
        </div>
        <h1 style={{
          fontSize: 'clamp(2.2rem, 5vw, 3.2rem)', fontWeight: 800, letterSpacing: '-0.04em',
          fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
          margin: '0 0 1.5rem', lineHeight: 1.08,
        }}>
          Harness engineering for the agent-first world
        </h1>
        <p style={{ fontSize: '1.15rem', color: 'var(--ma-muted)', lineHeight: 1.8, margin: 0, maxWidth: 600 }}>
          Over the past year, something fundamental changed in how software gets built. The bottleneck is no longer writing code. It's designing environments where agents can do reliable work.
        </p>
      </section>

      {/* ── Narrative sections ── */}

      {/* 1 — The shift */}
      <section style={{ maxWidth: 740, margin: '0 auto', padding: '0 2rem 3.5rem' }}>
        {heading('The role of the engineer is changing')}
        <p style={prose}>
          For decades, software engineering meant writing code. Reading requirements, thinking through edge cases, typing out implementations, running tests, fixing what broke. The craft was in the keystrokes.
        </p>
        <p style={prose}>
          That's shifting. When a coding agent can clone a repo, read the codebase, write an implementation, run the test suite, and open a pull request — all in minutes — the engineer's value moves upstream. You stop being the person who writes the code. You become the person who designs the system that makes agents effective.
        </p>
        <p style={prose}>
          Maestro is built around this idea. Humans steer. Agents execute.
        </p>
      </section>

      {/* 2 — Separation */}
      <section style={{ background: 'var(--ma-surface)', padding: '3.5rem 2rem' }}>
        <div style={{ maxWidth: 740, margin: '0 auto' }}>
          {heading('One agent per job')}
          <p style={prose}>
            A single monolithic agent that tries to implement, review, assess risk, deploy, and monitor will fail. Context windows are finite. Attention is scarce. The same reasons you wouldn't ask one engineer to do everything apply to agents.
          </p>
          <p style={prose}>
            Maestro decomposes the pipeline into five dedicated agents. Each has a focused system prompt, clear inputs, and a single responsibility. The Implementation Agent writes code. The Review Agent reads it. The Risk Profile Agent scores it. The Deployment Agent ships it. The Monitor Agent watches what happens after.
          </p>
          <p style={{ ...prose, margin: 0 }}>
            Separation of concerns isn't just a code principle. It's an agent principle.
          </p>
        </div>
      </section>

      {/* 3 — Same tools */}
      <section style={{ maxWidth: 740, margin: '0 auto', padding: '3.5rem 2rem' }}>
        {heading('No special channels')}
        <p style={prose}>
          When a human reviewer posts an inline comment on a pull request, they use the GitHub API. When Maestro's Review Agent does the same thing, it uses the same API. It checks out the PR, reads every changed file, and posts comments on specific lines of code — the exact same workflow.
        </p>
        <p style={prose}>
          When the Implementation Agent fixes the issue, it replies directly in the PR thread. When the Review Agent verifies the fix, it resolves the conversation via GitHub's GraphQL API and approves the PR.
        </p>
        <p style={{ ...prose, margin: 0 }}>
          There is no separate agent log you need to consult. The pull request <em>is</em> the record. You can read the history and understand what happened, whether the author was a person or an agent.
        </p>
      </section>

      {/* 4 — Speed */}
      <section style={{ background: '#1a1612', padding: '3.5rem 2rem' }}>
        <div style={{ maxWidth: 740, margin: '0 auto' }}>
          <h2 style={{
            fontSize: 'clamp(1.5rem, 3vw, 1.9rem)', fontWeight: 800, letterSpacing: '-0.03em',
            fontFamily: "'DM Sans', sans-serif", color: '#e8e0d4',
            margin: '0 0 1rem', lineHeight: 1.15,
          }}>
            Corrections are cheap. Waiting is expensive.
          </h2>
          <p style={{ ...prose, color: '#a89880' }}>
            In traditional engineering, you block merges until everything is perfect. Code review is a gate. CI is a gate. QA is a gate. Every gate adds latency.
          </p>
          <p style={{ ...prose, color: '#a89880' }}>
            In high-throughput agent systems, the math changes. The cost of a follow-up fix is almost always lower than the cost of blocking progress. Review agents catch issues. Implementation agents fix them. The loop continues — often in minutes, not days.
          </p>
          <p style={{ ...prose, color: '#a89880', margin: 0 }}>
            This would be irresponsible in a low-throughput environment. When agent throughput exceeds human attention by an order of magnitude, it's the right tradeoff.
          </p>
        </div>
      </section>

      {/* 5 — Risk */}
      <section style={{ maxWidth: 740, margin: '0 auto', padding: '3.5rem 2rem' }}>
        {heading('Risk is scored, not assumed')}
        <p style={prose}>
          Not every change needs a human in the loop. A one-line copy fix and a database migration rewrite are not the same thing. Treating them the same — either blocking everything or auto-approving everything — is wrong.
        </p>
        <p style={prose}>
          Maestro's Risk Profile Agent scores every pull request across seven dimensions before it can be merged:
        </p>

        {/* Risk cards */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: '0.75rem', margin: '0 0 1.5rem',
        }}>
          {[
            ['Scope', 'Files and lines changed'],
            ['Blast radius', 'Systems and users affected'],
            ['Complexity', 'New abstractions introduced'],
            ['Test coverage', 'Tests for changed paths'],
            ['Security', 'Auth, crypto, PII, secrets'],
            ['Reversibility', 'Can it be rolled back?'],
            ['Dependencies', 'External packages changed'],
          ].map(([dim, desc]) => (
            <div key={dim} style={{
              padding: '0.85rem 1rem', borderRadius: '0.5rem',
              background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
            }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.2rem' }}>{dim}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--ma-muted)', lineHeight: 1.5 }}>{desc}</div>
            </div>
          ))}
        </div>

        <p style={{ ...prose, margin: 0 }}>
          Low-risk changes auto-approve. Medium and above escalate to a human reviewer. The threshold is configurable per workspace. Risk becomes a number, not a feeling.
        </p>
      </section>

      {/* 6 — Observability */}
      <section style={{ background: 'var(--ma-surface)', padding: '3.5rem 2rem' }}>
        <div style={{ maxWidth: 740, margin: '0 auto' }}>
          {heading('Observability is not optional')}
          <p style={prose}>
            Deploying code is not the finish line. It's the beginning of a new question: did it work?
          </p>
          <p style={prose}>
            After every merge, Maestro's Monitor Agent watches. It checks Datadog dashboards for latency spikes and error rate changes. It queries Splunk logs for new exceptions. It does this for 15 minutes — long enough to catch slow-burn regressions that don't show up in the first few seconds.
          </p>
          <p style={{ ...prose, margin: 0 }}>
            Deploy confidence comes from automated post-deploy verification, not hope.
          </p>
        </div>
      </section>

      {/* 7 — Closing */}
      <section style={{ maxWidth: 740, margin: '0 auto', padding: '3.5rem 2rem 5rem' }}>
        {heading('The pipeline is the product')}
        <p style={prose}>
          These ideas are not abstract principles pinned to a wall. They are encoded directly into the system.
        </p>

        {/* Pipeline visual */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: '0', flexWrap: 'nowrap', margin: '1.5rem 0 2rem',
          padding: '1.5rem', borderRadius: '0.75rem',
          background: '#1a1612',
        }}>
          {[
            { name: 'Implement', color: '#2563eb' },
            { name: 'Review', color: '#d97706' },
            { name: 'Risk', color: '#7c3aed' },
            { name: 'Deploy', color: '#059669' },
            { name: 'Monitor', color: '#0891b2' },
          ].map((s, i, arr) => (
            <div key={s.name} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '0.5rem 1rem', borderRadius: '0.4rem',
                background: '#242018', border: `1px solid ${s.color}30`,
                textAlign: 'center',
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: s.color, margin: '0 auto 0.35rem',
                  boxShadow: `0 0 10px ${s.color}40`,
                }} />
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e8e0d4' }}>{s.name}</div>
              </div>
              {i < arr.length - 1 && (
                <span style={{ color: '#706555', fontSize: '0.65rem', padding: '0 0.4rem' }}>&rarr;</span>
              )}
            </div>
          ))}
        </div>

        <p style={prose}>
          Each transition is an explicit handoff. Each agent has its own system prompt, model, and configuration. The pipeline is visible, auditable, and configurable — not a black box.
        </p>
        <p style={{ ...prose, margin: 0 }}>
          This is what we mean by harness engineering: building the scaffolding that makes agents effective, rather than writing the code yourself. The discipline shows up in the system design, not the syntax.
        </p>
      </section>

    </Layout>
  );
}
