# Nexora HQ — Parent Company Architecture

## Purpose

Nexora is the parent company. Nexora HQ will be a separate application/repository that provides oversight of exactly two core ventures:

1. **AI Software Developer** — the software-building venture currently developed in the `AI-Software-Company` repository.
2. **AI Open Source Contributor** — the open-source contribution venture currently developed in the `AI-OpenSource-Engineer-` repository.

These are the only venture cards in Nexora HQ.

## Explicit boundaries

- Nexora HQ monitors the health and progress of the two ventures; it does not run their internal workflows.
- AI Software Developer owns its factory, missions, generated applications, previews, QA, and deployments.
- Generated applications are not listed as ventures in Nexora HQ.
- AI Open Source Contributor owns its contribution queue, repository activity, checks, and human approval workflow.
- Do not duplicate AI Software Developer as two ventures named "AI Software Company" and "AI Software Maker". Use the approved display name **AI Software Developer** for the venture.
- The existing repository names remain unchanged until a deliberate repository migration is planned.

## HQ dashboard requirements

- Two venture cards only, with explicit connected / degraded / unavailable states.
- Last successful sync time, latest verified activity, health summary, and links to each venture's own dashboard/repository.
- Integration status and actionable errors when a source is unavailable.
- No invented health, usage, revenue, deployment, or activity metrics.
- Read-only integrations by default; HQ should not trigger builds, merge PRs, deploy, or approve contributions.
- Keep generated-app details inside AI Software Developer.
- Owner authentication, least-privilege access, secret management via environment configuration, and audit logging for HQ configuration changes.

## Integration contract

Build a small adapter per venture. Each adapter should return a normalized snapshot:

- `venture_id`
- `display_name`
- `repository_url`
- `dashboard_url`
- `connection_status`
- `last_successful_sync_at`
- `health_status`
- `latest_activity_summary`
- `source_updated_at`
- `error` (nullable; safe, non-secret diagnostic)

A missing or failed integration must render as **Unavailable** with its error, never as healthy by default. Store no credentials in source control. Prefer narrow, read-only tokens and documented API endpoints.

## Delivery order

1. Stabilize the two venture applications independently.
2. Build Nexora HQ as a separate repository/application with the two-card dashboard and honest disconnected states.
3. Implement and test the read-only adapters individually.
4. Connect both adapters and verify that only the two ventures appear in HQ.
5. Test auth boundaries, source outages, stale data, secret handling, and audit records.
6. Enable monitoring only after each integration passes validation.

## Current status

This file records the architecture contract only. It does not claim that Nexora HQ exists, that integrations are connected, or that either venture is currently healthy. The GitHub integration available for this work does not expose a repository-creation action, so the actual standalone Nexora HQ repository must be created before its application scaffold is committed.
