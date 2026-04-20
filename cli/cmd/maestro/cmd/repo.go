package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

var agentsTemplates = map[string]string{
	"SPECIFICATION.md": `# Specification

> **Agents: Planner (produces) · Implementer · Reviewer · QA (validates against)**

## Feature: <!-- FILL: feature name -->

### Problem Statement
<!-- FILL: What problem does this solve? Why now? Who is affected? -->

### Proposed Solution
<!-- FILL: High-level approach. What changes, what doesn't. -->

### Acceptance Criteria
- [ ] <!-- FILL: criterion 1 -->
- [ ] <!-- FILL: criterion 2 -->

### Out of Scope
<!-- FILL: What this change explicitly does NOT include -->

### Dependencies & Risks
<!-- FILL: Other systems this depends on. What could go wrong? -->
`,
	"ARCHITECTURE.md": `# Architecture

> **Agents: Planner · Implementer · Reviewer · Risk**

## Overview
<!-- FILL: One paragraph describing what this application does. -->

## Directory Structure
<!-- FILL: Run ` + "`find . -type d -maxdepth 3`" + ` and document what matters. -->

## Service Boundaries
| Service / Module | Responsibility | Communicates With |
|------------------|---------------|-------------------|
| <!-- FILL -->    |               |                   |

## Data Flow
<!-- FILL: Trace a typical request. Name actual files and functions. -->

## External Dependencies
| System | Protocol | Purpose | Failure Mode |
|--------|----------|---------|--------------|
| <!-- FILL --> | | | |

## Key Design Decisions
<!-- FILL: Architectural choices and WHY. Include dates if known. -->
`,
	"DATABASE.md": `# Database

> **Agents: Planner · Implementer · Risk**

## Engine & ORM
<!-- FILL: e.g. "PostgreSQL 16 via SQLAlchemy 2.0 (async)" -->

## Schema Overview
| Table | Purpose | Key Columns | Relationships |
|-------|---------|-------------|---------------|
| <!-- FILL --> | | | |

## Migration Strategy
<!-- FILL: How schema changes are applied. -->

## Indexing
<!-- FILL: List indexes and WHY each exists. -->

## Conventions
<!-- FILL: e.g. "All tables have created_at/updated_at", "Use Text not VARCHAR" -->
`,
	"API_CONTRACTS.md": `# API Contracts

> **Agents: Planner · QA (validates against)**

## Base URL & Versioning
<!-- FILL: e.g. "/api/v1", versioned via URL path -->

## Authentication
<!-- FILL: e.g. "Bearer JWT in Authorization header" -->

## Error Format
` + "```json" + `
{"detail": "Human-readable error message"}
` + "```" + `

## Conventions
<!-- FILL: Naming, pagination, filtering patterns. -->

## Key Endpoints
<!-- FILL: Document conventions, not exhaustive listing. Link to OpenAPI if available. -->
`,
	"STYLE_GUIDE.md": `# Style Guide

> **Agents: Implementer · Reviewer**

## Language & Framework
<!-- FILL: e.g. "TypeScript 5 / React 19 / Next.js 16" -->

## Formatting
<!-- FILL: Tool and config. e.g. "Prettier with .prettierrc" -->

## Naming Conventions
| Element | Convention | Example |
|---------|-----------|---------|
| <!-- FILL --> | | |

## Import Order
<!-- FILL: e.g. "1. stdlib, 2. third-party, 3. internal" -->

## Patterns to Follow
<!-- FILL: What this codebase does consistently. -->

## Patterns to Avoid
<!-- FILL: Anti-patterns agents must never introduce. -->
`,
	"SECURITY.md": `# Security

> **Agents: Implementer · Reviewer · Risk**

## Authentication
<!-- FILL: How users authenticate. -->

## Authorization
<!-- FILL: How permissions are enforced. -->

## Secrets Management
<!-- FILL: Where secrets live, how accessed. Never log secrets. -->

## Input Validation
<!-- FILL: e.g. "Pydantic models for all API bodies", "Parameterized SQL only" -->

## OWASP Checklist
- [ ] Injection
- [ ] Broken Auth
- [ ] Sensitive Data Exposure
- [ ] XSS
- [ ] CSRF
`,
	"COMPLIANCE.md": `# Compliance

> **Agents: Implementer · Reviewer · Risk**

## Regulatory Framework
<!-- FILL: e.g. "GDPR", "SOC 2", "HIPAA", or "None currently" -->

## PII Handling
<!-- FILL: What is PII here and how it's protected. -->

## Data Residency
<!-- FILL: Where data must be stored geographically. -->

## Audit Trail
<!-- FILL: What actions are logged for audit. -->

## Data Retention
<!-- FILL: How long different data types are kept. -->
`,
	"TEST_STRATEGY.md": `# Test Strategy

> **Agents: QA (primary)**

## Framework
<!-- FILL: e.g. "pytest", "vitest", "Playwright" -->

## Running Tests
` + "```bash" + `
# FILL: exact commands
` + "```" + `

## Test Types
| Type | Location | Coverage Target | When to Write |
|------|----------|----------------|---------------|
| <!-- FILL --> | | | |

## What to Test / What NOT to Test
<!-- FILL: Concrete guidance. -->

## Fixtures & Helpers
<!-- FILL: Common test utilities available. -->
`,
	"RUNBOOK.md": `# Runbook

> **Agents: Risk · Deploy · Monitor**

## Health Checks
<!-- FILL: How to verify the system is healthy. -->

## Common Issues
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| <!-- FILL --> | | |

## Incident Response
<!-- FILL: Step-by-step procedure. -->

## Escalation
<!-- FILL: Who to contact and when. -->

## Rollback Procedure
<!-- FILL: How to roll back a bad deploy. -->
`,
	"DEPLOY.md": `# Deploy

> **Agents: Deploy (primary)**

## Environments
| Environment | URL | Purpose | Deploy Trigger |
|-------------|-----|---------|---------------|
| <!-- FILL --> | | | |

## Deploy Process
<!-- FILL: Step-by-step. -->

## CI/CD Pipeline
<!-- FILL: What checks must pass. How deploy is triggered. -->

## Feature Flags
<!-- FILL: How feature flags work, if applicable. -->

## Required Secrets
<!-- FILL: Secret names needed for deploy (not values). -->
`,
	"MONITORING.md": `# Monitoring

> **Agents: Monitor (primary)**

## Key Metrics
| Metric | Baseline | Alert Threshold | Dashboard |
|--------|----------|----------------|-----------|
| <!-- FILL --> | | | |

## SLOs
<!-- FILL: e.g. "99.9% uptime", "p95 < 300ms" -->

## Dashboards
<!-- FILL: Where to find them. -->

## Alerting
<!-- FILL: How alerts work and who gets them. -->

## Post-Deploy Monitoring
<!-- FILL: What to watch after a deploy. -->
`,
}

var repoCmd = &cobra.Command{
	Use:   "repo",
	Short: "Repository agent configuration",
}

var repoInitCmd = &cobra.Command{
	Use:   "init [path]",
	Short: "Scaffold .agents/ directory with template files",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		force, _ := cmd.Flags().GetBool("force")

		target := "."
		if len(args) > 0 {
			target = args[0]
		}
		agentsDir := filepath.Join(target, ".agents")

		if err := os.MkdirAll(agentsDir, 0o755); err != nil {
			return err
		}

		var created, skipped []string
		for filename, content := range agentsTemplates {
			fp := filepath.Join(agentsDir, filename)
			if _, err := os.Stat(fp); err == nil && !force {
				skipped = append(skipped, filename)
				continue
			}
			if err := os.WriteFile(fp, []byte(content), 0o644); err != nil {
				return fmt.Errorf("failed to write %s: %w", filename, err)
			}
			created = append(created, filename)
		}

		if len(created) > 0 {
			fmt.Printf("Created .agents/ files in %s:\n", agentsDir)
			for _, f := range created {
				fmt.Printf("  + %s\n", f)
			}
		}
		if len(skipped) > 0 {
			fmt.Println("Skipped (already exist, use --force to overwrite):")
			for _, f := range skipped {
				fmt.Printf("  - %s\n", f)
			}
		}
		return nil
	},
}

func init() {
	repoInitCmd.Flags().Bool("force", false, "Overwrite existing files")
	repoCmd.AddCommand(repoInitCmd)
	rootCmd.AddCommand(repoCmd)
}
