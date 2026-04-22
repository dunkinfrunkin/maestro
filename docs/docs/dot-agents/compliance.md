---
sidebar_position: 7
title: COMPLIANCE.md
---

# COMPLIANCE.md

**Read by:** Implementer, Reviewer, Risk

## Why it exists

Compliance requirements are invisible constraints that agents will violate if they don't know about them. An agent might store PII in a log, send data to a region it shouldn't, or skip an audit trail entry. These aren't code bugs - they're regulatory violations that can have real consequences.

If your project operates under GDPR, SOC 2, HIPAA, or any regulatory framework, this file makes those constraints explicit so agents never cross them.

## What to include

- **Regulatory framework** - Which regulations apply (or "None currently")
- **PII handling** - What constitutes PII and how it's protected
- **Data residency** - Geographic restrictions on data storage
- **Audit trail** - What actions must be logged for compliance
- **Data retention** - How long different data types are kept

## Example

```markdown
# Compliance

## Regulatory Framework
SOC 2 Type II. Annual audit. No HIPAA or GDPR currently.

## PII Handling
PII fields: email, name, IP address. All PII encrypted at rest.
Never log PII. Never include PII in error messages or stack traces.

## Data Residency
All data stored in US-East-1 (AWS). No cross-region replication.

## Audit Trail
Log all: user login, workspace creation, connection changes,
agent runs, task status transitions. Logs retained 1 year.

## Data Retention
- Agent run logs: 90 days
- Task records: indefinite
- User sessions: 30 days
- Deleted workspace data: 30-day soft delete, then purged
```
