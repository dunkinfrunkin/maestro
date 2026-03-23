import {type ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

/* ── Pipeline steps ── */

const PIPELINE_STEPS = [
  {icon: '\u{1F4CB}', name: 'Queued',    desc: 'Task created from issue or manual input'},
  {icon: '\u{1F528}', name: 'Implement', desc: 'Agent writes code and opens a PR'},
  {icon: '\u{1F50D}', name: 'Review',    desc: 'Inline code review with comments'},
  {icon: '\u{1F4CA}', name: 'Risk',      desc: 'Score complexity, blast radius, coverage'},
  {icon: '\u{1F680}', name: 'Deploy',    desc: 'Merge PR and run CI/CD pipeline'},
  {icon: '\u{1F4E1}', name: 'Monitor',   desc: 'Watch logs and metrics post-deploy'},
];

/* ── Features ── */

const FEATURES = [
  {
    icon: '\u{1F504}',
    title: 'Multi-agent pipeline',
    desc: 'Each task flows through implementation, review, risk profiling, deployment, and monitoring stages automatically.',
  },
  {
    icon: '\u{1F4DD}',
    title: 'Inline PR code reviews',
    desc: 'Review agent reads diffs and leaves inline comments on specific lines, just like a human reviewer.',
  },
  {
    icon: '\u{1F4AC}',
    title: 'Comment thread conversations',
    desc: 'Agents and humans can reply to review comments, creating threaded discussions that drive fixes.',
  },
  {
    icon: '\u{2699}\u{FE0F}',
    title: 'Configurable prompts & models',
    desc: 'Customize the system prompt and model for each agent per-project. Swap Claude for GPT or local models.',
  },
  {
    icon: '\u{1F517}',
    title: 'GitHub & Linear integrations',
    desc: 'Create tasks from GitHub issues or Linear tickets. PRs sync back automatically.',
  },
  {
    icon: '\u{1F9E9}',
    title: 'Plugin framework',
    desc: 'Build custom agents with Python entry points. Drop in linters, security scanners, or notification hooks.',
  },
];

/* ── Tech stack ── */

const TECH = [
  {icon: '\u{1F40D}', label: 'Python / FastAPI'},
  {icon: '\u{269B}\u{FE0F}',  label: 'Next.js'},
  {icon: '\u{1F418}', label: 'PostgreSQL'},
  {icon: '\u{1F916}', label: 'Claude Code CLI'},
];

/* ════════════════════════════════════════
   PAGE
   ════════════════════════════════════════ */

export default function Home(): ReactNode {
  return (
    <Layout
      title="Maestro - Autonomous coding agent orchestration"
      description="Autonomous coding agent orchestration for enterprise teams. Multi-agent pipeline for implementation, review, risk profiling, and deployment."
    >
    <div className={styles.pageWrap}>

      {/* ── Hero ── */}
      <section className={styles.hero}>
        <div className={styles.heroGlow} />
        <div className={styles.heroInner}>
          <div className={styles.heroBadge}>
            <span className={styles.heroBadgeDot} />
            Currently under active development
          </div>
          <Heading as="h1" className={styles.heroTitle}>
            <span className={styles.heroGradient}>Maestro</span>
          </Heading>
          <p className={styles.heroTagline}>
            Autonomous coding agent orchestration for enterprise teams.
            <br />
            From issue to deployed code — reviewed, risk-scored, and monitored.
          </p>
          <div className={styles.heroButtons}>
            <Link className={clsx('button button--primary button--lg', styles.heroPrimary)} to="/docs/getting-started">
              Get Started
            </Link>
            <Link className={clsx('button button--secondary button--lg', styles.heroSecondary)} to="https://github.com/dunkinfrunkin/maestro">
              GitHub
            </Link>
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* ── Pipeline visualization ── */}
      <section className={styles.pipeline}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>How it works</span>
            <Heading as="h2" className={styles.sectionTitle}>The Harness Engineering Pipeline</Heading>
            <p className={styles.sectionSubtitle}>
              Every task flows through a deterministic pipeline. Agents handle each stage, with review loops until the code is ready.
            </p>
          </div>
          <div className={styles.pipelineFlow}>
            {PIPELINE_STEPS.map((step, i) => (
              <span key={step.name} style={{display: 'contents'}}>
                <div className={styles.pipelineStep}>
                  <div className={styles.pipelineIcon}>{step.icon}</div>
                  <div className={styles.pipelineStepName}>{step.name}</div>
                  <div className={styles.pipelineStepDesc}>{step.desc}</div>
                </div>
                {i === 1 && <div className={styles.pipelineArrow}>{'\u2192'}</div>}
                {i === 2 && <div className={styles.pipelineLoop}>{'\u21C4'} loop</div>}
                {i !== 1 && i !== 2 && i < PIPELINE_STEPS.length - 1 && (
                  <div className={styles.pipelineArrow}>{'\u2192'}</div>
                )}
              </span>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* ── Example task run ── */}
      <section className={styles.taskRun}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>Example</span>
            <Heading as="h2" className={styles.sectionTitle}>A Task in Action</Heading>
            <p className={styles.sectionSubtitle}>
              Watch a real task flow through the pipeline from issue to deployment.
            </p>
          </div>
          <div className={styles.timeline}>

            {/* Issue created */}
            <div className={styles.timelineEntry}>
              <div className={clsx(styles.timelineDot, styles.timelineDotBlue)} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F4CB}'} Queued</div>
                <div className={styles.timelineTitle}>Add search endpoint: GET /books/search?q=term</div>
                <div className={styles.timelineBody}>
                  Task created from GitHub issue #42. Assigned to workspace <strong>acme-api</strong>.
                </div>
              </div>
            </div>

            {/* Implement */}
            <div className={styles.timelineEntry}>
              <div className={styles.timelineDot} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F528}'} Implement</div>
                <div className={styles.timelineTitle}>Agent reads codebase and writes implementation</div>
                <div className={styles.timelineBody}>
                  Implementation agent reads existing routes, models, and tests. Creates PR #87.
                </div>
                <code className={styles.timelineCode}>
{`# app/routes/books.py
@router.get("/books/search")
async def search_books(q: str, db: Session = Depends(get_db)):
    results = db.query(Book).filter(
        Book.title.ilike(f"%{q}%")
    ).limit(50).all()
    return {"books": results, "count": len(results)}`}
                </code>
              </div>
            </div>

            {/* Review — issue found */}
            <div className={styles.timelineEntry}>
              <div className={clsx(styles.timelineDot, styles.timelineDotGold)} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F50D}'} Review</div>
                <div className={styles.timelineTitle}>Code review finds missing validation</div>
                <div className={styles.timelineBody}>
                  Review agent analyzes the diff and leaves an inline comment.
                </div>
                <div className={styles.timelineComment}>
                  <span className={styles.timelineCommentIcon}>{'\u{1F4AC}'}</span>
                  <span>
                    <strong>review-agent</strong> on <code>books.py:3</code>
                    <br />
                    Missing input validation for empty query parameter. <code>q=""</code> will return all rows — add a check.
                  </span>
                </div>
              </div>
            </div>

            {/* Implement follow-up */}
            <div className={styles.timelineEntry}>
              <div className={styles.timelineDot} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F528}'} Implement (follow-up)</div>
                <div className={styles.timelineTitle}>Agent applies fix for review feedback</div>
                <code className={styles.timelineCode}>
{`+  if not q or not q.strip():
+      raise HTTPException(400, "Query parameter 'q' must not be empty")`}
                </code>
              </div>
            </div>

            {/* Re-review */}
            <div className={styles.timelineEntry}>
              <div className={clsx(styles.timelineDot, styles.timelineDotGreen)} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F50D}'} Review (re-review)</div>
                <div className={styles.timelineTitle}>Verified — fix looks good</div>
                <div className={styles.timelineSuccess}>
                  {'\u2705'} All review comments resolved. Approved.
                </div>
              </div>
            </div>

            {/* Risk profile */}
            <div className={styles.timelineEntry}>
              <div className={clsx(styles.timelineDot, styles.timelineDotPurple)} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F4CA}'} Risk Profile</div>
                <div className={styles.timelineTitle}>Risk assessment: LOW</div>
                <table className={styles.riskTable}>
                  <tbody>
                    <tr><td>Complexity</td><td className={styles.riskLow}>LOW</td></tr>
                    <tr><td>Blast radius</td><td className={styles.riskLow}>1 route, 0 shared utils</td></tr>
                    <tr><td>Test coverage</td><td className={styles.riskLow}>3 new tests added</td></tr>
                    <tr><td>Overall</td><td className={styles.riskLow}>LOW — safe to auto-merge</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Deploy */}
            <div className={styles.timelineEntry}>
              <div className={clsx(styles.timelineDot, styles.timelineDotGreen)} />
              <div className={styles.timelineCard}>
                <div className={styles.timelinePhase}>{'\u{1F680}'} Deploy</div>
                <div className={styles.timelineTitle}>PR #87 merged, CI passing</div>
                <div className={styles.timelineSuccess}>
                  {'\u2705'} Deployed to production. All checks green.
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* ── Features grid ── */}
      <section className={styles.features}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>Features</span>
            <Heading as="h2" className={styles.sectionTitle}>Built for Real Engineering</Heading>
            <p className={styles.sectionSubtitle}>
              Not a toy demo. Maestro runs the full software development lifecycle with configurable agents.
            </p>
          </div>
          <div className={styles.featuresGrid}>
            {FEATURES.map(f => (
              <div key={f.title} className={styles.featureCard}>
                <div className={styles.featureIcon}>{f.icon}</div>
                <div className={styles.featureTitle}>{f.title}</div>
                <p className={styles.featureDesc}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.divider} />

      {/* ── Tech stack ── */}
      <section className={styles.techStack}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>Stack</span>
            <Heading as="h2" className={styles.sectionTitle}>Built With</Heading>
          </div>
          <div className={styles.techList}>
            {TECH.map(t => (
              <div key={t.label} className={styles.techItem}>
                <span className={styles.techIcon}>{t.icon}</span>
                {t.label}
              </div>
            ))}
          </div>
        </div>
      </section>

    </div>
    </Layout>
  );
}
