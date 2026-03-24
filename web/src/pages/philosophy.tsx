import Layout from '@theme/Layout';

export default function Philosophy() {
  const section = (title: string, body: string[]) => (
    <div style={{ padding: '2rem 0', borderTop: '1px solid var(--ma-border)' }}>
      <h3 style={{
        fontSize: '1.15rem', fontWeight: 700, color: 'var(--ma-fg)',
        fontFamily: "'DM Sans', sans-serif", margin: '0 0 0.75rem', lineHeight: 1.3,
      }}>
        {title}
      </h3>
      {body.map((p, i) => (
        <p key={i} style={{ fontSize: '0.92rem', color: 'var(--ma-muted)', lineHeight: 1.8, margin: '0 0 0.75rem' }}>
          {p}
        </p>
      ))}
    </div>
  );

  return (
    <Layout title="Philosophy" description="Design principles behind Maestro">
      <article style={{ maxWidth: 720, margin: '0 auto', padding: '4rem 2rem 5rem' }}>

        {/* Header */}
        <div style={{ marginBottom: '2.5rem' }}>
          <div style={{
            fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.1em', color: 'var(--ma-muted)', marginBottom: '0.75rem',
          }}>
            Philosophy
          </div>
          <h1 style={{
            fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 800, letterSpacing: '-0.04em',
            fontFamily: "'DM Sans', sans-serif", color: 'var(--ma-fg)',
            margin: '0 0 1rem', lineHeight: 1.1,
          }}>
            Harness engineering for the agent-first world
          </h1>
          <p style={{ fontSize: '1.05rem', color: 'var(--ma-muted)', lineHeight: 1.75, margin: 0 }}>
            When agents handle the software lifecycle, the engineer's job shifts from writing code to designing systems where agents can do reliable work. Maestro encodes that shift into a pipeline.
          </p>
        </div>

        {/* Principles */}
        {section('Humans steer. Agents execute.', [
          'Engineers define intent, set constraints, and review outcomes. Agents handle the implementation, review, testing, and deployment. The bottleneck shifts from writing code to designing environments where agents can do reliable work.',
          'When something fails, the fix is almost never "try harder." The right question is always: what capability is missing, and how do we make it legible and enforceable for the agent?',
        ])}

        {section('Every agent gets its own role', [
          "A single monolithic agent can't hold the full context of implementation, review, risk assessment, and deployment. Maestro decomposes the pipeline into dedicated agents — Implementation, Review, Risk Profile, Deployment, and Monitor — each with a focused system prompt, clear inputs, and a single responsibility.",
          "This mirrors how effective engineering organizations work. You don't ask one person to write the code, review it, assess the risk, and monitor the deploy. Separation of concerns applies to agents just as well as it applies to code.",
        ])}

        {section('Agents talk through the same tools humans use', [
          "Review comments, PR threads, CI checks, GitHub API calls. Agents don't use special channels. They post inline comments on specific lines of code, reply in threads, resolve conversations, and approve pull requests — the same workflow as human developers.",
          "This has a practical consequence: you can read the PR history and understand what happened, whether the author was a person or an agent. There is no separate agent log you need to consult. The pull request is the record.",
        ])}

        {section('Corrections are cheap. Waiting is expensive.', [
          'In high-throughput agent systems, the cost of a follow-up fix is almost always lower than the cost of blocking progress. Maestro favors fast iteration over gated perfection.',
          'Review agents catch issues. Implementation agents fix them. The loop continues. This would be irresponsible in a low-throughput environment. In a system where agent throughput far exceeds human attention, it is often the right tradeoff.',
        ])}

        {section('Risk is scored, not assumed', [
          'Not every change needs a human in the loop. And not every change should be auto-approved.',
          'Maestro scores each PR across seven dimensions: scope, blast radius, complexity, test coverage, security, reversibility, and dependencies. Low-risk changes auto-approve. Medium and above escalate to a human reviewer. The threshold is configurable per workspace.',
        ])}

        {/* Risk table */}
        <div style={{
          margin: '-0.5rem 0 1.5rem', borderRadius: '0.5rem', overflow: 'hidden',
          border: '1px solid var(--ma-border)',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', margin: 0 }}>
            <thead>
              <tr style={{ background: 'var(--ma-surface)' }}>
                <th style={{ padding: '0.6rem 1rem', fontSize: '0.75rem', fontWeight: 600, textAlign: 'left', color: 'var(--ma-fg)' }}>Dimension</th>
                <th style={{ padding: '0.6rem 1rem', fontSize: '0.75rem', fontWeight: 600, textAlign: 'left', color: 'var(--ma-fg)' }}>What it measures</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Scope', 'Number of files and lines changed'],
                ['Blast radius', 'How many systems or users are affected'],
                ['Complexity', 'Cyclomatic complexity, new abstractions'],
                ['Test coverage', 'Whether tests exist for changed paths'],
                ['Security', 'Auth, crypto, PII, secrets handling'],
                ['Reversibility', 'Can this be rolled back cleanly?'],
                ['Dependencies', 'New or updated external dependencies'],
              ].map(([dim, desc], i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--ma-border)' }}>
                  <td style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', fontWeight: 500, color: 'var(--ma-fg)' }}>{dim}</td>
                  <td style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', color: 'var(--ma-muted)' }}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {section('Observability is not optional', [
          "Deploying code is not the finish line. Maestro's Monitor agent checks Datadog dashboards and Splunk logs for 15 minutes after every deploy. If latency spikes or error rates climb, it flags the change.",
          'Deploy confidence comes from automated post-deploy verification, not hope.',
        ])}

        {section('The pipeline is the product', [
          'These principles are not abstract. They are encoded directly into the pipeline.',
        ])}

        {/* Pipeline diagram */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: '0.5rem', flexWrap: 'wrap', margin: '0 0 1.5rem',
          padding: '1.25rem', borderRadius: '0.5rem',
          background: 'var(--ma-surface)', border: '1px solid var(--ma-border)',
        }}>
          {['Issue', 'Implement', 'Review', 'Risk Profile', 'Deploy', 'Monitor'].map((stage, i, arr) => (
            <span key={stage} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                fontSize: '0.78rem', fontWeight: 600, color: 'var(--ma-fg)',
                padding: '0.3rem 0.65rem', borderRadius: '0.35rem',
                background: 'var(--ma-bg)', border: '1px solid var(--ma-border)',
              }}>
                {stage}
              </span>
              {i < arr.length - 1 && (
                <span style={{ color: 'var(--ma-muted)', fontSize: '0.75rem' }}>&rarr;</span>
              )}
            </span>
          ))}
        </div>

        <p style={{ fontSize: '0.92rem', color: 'var(--ma-muted)', lineHeight: 1.8, margin: 0 }}>
          Each transition is an explicit handoff from one agent to the next. Each agent has its own system prompt, model selection, and configuration. The pipeline is visible, auditable, and configurable — not a black box. This is what we mean by harness engineering: building the scaffolding that makes agents effective, rather than writing the code yourself.
        </p>

      </article>
    </Layout>
  );
}
