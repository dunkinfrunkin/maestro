import Layout from '@theme/Layout';

export default function Philosophy() {
  return (
    <Layout title="Philosophy" description="Design principles behind Maestro">
      <article style={{ maxWidth: 680, margin: '0 auto', padding: '5rem 2rem 6rem' }}>

        <div style={{
          fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '1rem',
        }}>
          Philosophy
        </div>

        <h1 style={{
          fontSize: 'clamp(2.2rem, 5vw, 3rem)', fontWeight: 800, letterSpacing: '-0.04em',
          fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
          margin: '0 0 1.5rem', lineHeight: 1.08,
        }}>
          Harness engineering for the agent-first world
        </h1>

        <p style={{ fontSize: '1.1rem', color: 'var(--ma-muted)', lineHeight: 1.85, margin: '0 0 3rem' }}>
          Over the past year, something fundamental changed in how software gets built. The bottleneck is no longer writing code. It's designing environments where agents can do reliable work. Maestro encodes that shift into a pipeline.
        </p>

        <Section title="The role of the engineer is changing">
          <P>For decades, software engineering meant writing code. Reading requirements, thinking through edge cases, typing out implementations, running tests, fixing what broke. The craft was in the keystrokes.</P>
          <P>That's shifting. When a coding agent can clone a repo, read the codebase, write an implementation, run the test suite, and open a pull request - all in minutes - the engineer's value moves upstream. You stop being the person who writes the code. You become the person who designs the system that makes agents effective.</P>
          <P last>Maestro is built around this idea. Humans steer. Agents execute.</P>
        </Section>

        <Section title="One agent per job">
          <P>A single monolithic agent that tries to implement, review, assess risk, deploy, and monitor will fail. Context windows are finite. Attention is scarce. The same reasons you wouldn't ask one engineer to do everything apply to agents.</P>
          <P>Maestro decomposes the pipeline into five dedicated agents. Each has a focused system prompt, clear inputs, and a single responsibility. The Implementation Agent writes code. The Review Agent reads it. The Risk Profile Agent scores it. The Deployment Agent ships it. The Monitor Agent watches what happens after.</P>
          <P last>Separation of concerns isn't just a code principle. It's an agent principle.</P>
        </Section>

        <Section title="No special channels">
          <P>When a human reviewer posts an inline comment on a pull request, they use the GitHub API. When Maestro's Review Agent does the same thing, it uses the same API. It checks out the PR, reads every changed file, and posts comments on specific lines of code - the exact same workflow.</P>
          <P>When the Implementation Agent fixes the issue, it replies directly in the PR thread. When the Review Agent verifies the fix, it resolves the conversation via GitHub's GraphQL API and approves the PR.</P>
          <P last>There is no separate agent log you need to consult. The pull request <em>is</em> the record. You can read the history and understand what happened, whether the author was a person or an agent.</P>
        </Section>

        <Section title="Corrections are cheap. Waiting is expensive.">
          <P>In traditional engineering, you block merges until everything is perfect. Code review is a gate. CI is a gate. QA is a gate. Every gate adds latency.</P>
          <P>In high-throughput agent systems, the math changes. The cost of a follow-up fix is almost always lower than the cost of blocking progress. Review agents catch issues. Implementation agents fix them. The loop continues - often in minutes, not days.</P>
          <P last>This would be irresponsible in a low-throughput environment. When agent throughput exceeds human attention by an order of magnitude, it's the right tradeoff.</P>
        </Section>

        <Section title="Risk is scored, not assumed">
          <P>Not every change needs a human in the loop. A one-line copy fix and a database migration rewrite are not the same thing. Treating them the same - either blocking everything or auto-approving everything - is wrong.</P>
          <P>Maestro's Risk Profile Agent scores every pull request across seven dimensions before it can be merged:</P>

          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
            gap: '0.6rem', margin: '0.25rem 0 1.5rem',
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
                padding: '0.75rem 0.85rem', borderRadius: '0.4rem',
                background: 'var(--ma-surface)',
              }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ma-fg)', marginBottom: '0.15rem' }}>{dim}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--ma-muted)', lineHeight: 1.5 }}>{desc}</div>
              </div>
            ))}
          </div>

          <P last>Low-risk changes auto-approve. Medium and above escalate to a human reviewer. The threshold is configurable per workspace. Risk becomes a number, not a feeling.</P>
        </Section>

        <Section title="Observability is not optional">
          <P>Deploying code is not the finish line. It's the beginning of a new question: did it work?</P>
          <P>After every merge, Maestro's Monitor Agent watches. It checks Datadog dashboards for latency spikes and error rate changes. It queries Splunk logs for new exceptions. It does this for 15 minutes - long enough to catch slow-burn regressions that don't show up in the first few seconds.</P>
          <P last>Deploy confidence comes from automated post-deploy verification, not hope.</P>
        </Section>

        <Section title="The pipeline is the product" last>
          <P>These ideas are not abstract principles pinned to a wall. They are encoded directly into the system.</P>

          {/* Pipeline visual */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '0', margin: '0.5rem 0 1.5rem',
            padding: '1.25rem 1rem', borderRadius: '0.6rem',
            background: 'var(--ma-surface)',
          }}>
            {[
              { name: 'Implement', color: '#2563eb' },
              { name: 'Review', color: '#d97706' },
              { name: 'Risk', color: '#7c3aed' },
              { name: 'Deploy', color: '#059669' },
              { name: 'Monitor', color: '#0891b2' },
            ].map((s, i, arr) => (
              <div key={s.name} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ textAlign: 'center', padding: '0 0.25rem' }}>
                  <div style={{
                    width: 7, height: 7, borderRadius: '50%',
                    background: s.color, margin: '0 auto 0.3rem',
                  }} />
                  <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--ma-fg)' }}>{s.name}</div>
                </div>
                {i < arr.length - 1 && (
                  <span style={{ color: 'var(--ma-muted)', fontSize: '0.6rem', padding: '0 0.5rem', marginTop: '-0.3rem' }}>&rarr;</span>
                )}
              </div>
            ))}
          </div>

          <P>Each transition is an explicit handoff. Each agent has its own system prompt, model, and configuration. The pipeline is visible, auditable, and configurable - not a black box.</P>
          <P last>This is what we mean by harness engineering: building the scaffolding that makes agents effective, rather than writing the code yourself. The discipline shows up in the system design, not the syntax.</P>
        </Section>

      </article>
    </Layout>
  );
}

/* ── Helpers ── */

function Section({ title, children, last }: { title: string; children: React.ReactNode; last?: boolean }) {
  return (
    <section style={{ marginBottom: last ? 0 : '2.5rem' }}>
      <h2 style={{
        fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em',
        fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
        margin: '0 0 0.85rem', lineHeight: 1.25,
      }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

function P({ children, last }: { children: React.ReactNode; last?: boolean }) {
  return (
    <p style={{
      fontSize: '1rem', color: 'var(--ma-muted)', lineHeight: 1.85,
      margin: last ? 0 : '0 0 1rem',
    }}>
      {children}
    </p>
  );
}
