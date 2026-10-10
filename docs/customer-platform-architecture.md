# Customer Platform, Demo, and Owner App Architecture

## Product boundary

The AI Software Company is the customer-facing product. Customers pay the company for access to an AI app-building factory. A limited demo is available before payment. The company owner has a separate private Owner App.

## Non-negotiable workspace boundaries

- **Company workspace:** company-owned projects, missions, factory configuration, operational records, and company memory.
- **Personal workspace:** each customer's own projects, missions, outputs, settings, history, and provider connections.
- **Demo workspace:** short-lived, resource-limited sandbox data; it must not read or write company or customer workspace data.
- **Owner App:** owner-only business and operational administration. Authorization is enforced server-side for every administrative API, not just by hiding navigation or routes.
- Never share a global GitHub credential as if it belonged to a customer. Login with Google does not grant GitHub repository access. GitHub repository authorization is a separate, explicit consent flow.
- Never trust a client-supplied user, workspace, role, plan, payment state, or quota. Resolve them from a validated server-side session and persisted records.
- Customer requests must not be able to select or mutate the company workspace by changing an ID or URL.
- Do not expose provider access tokens to browser JavaScript. Use secure server-side token storage, with encryption at rest before storing user provider credentials.

## Account and access lifecycle

1. Visitor enters demo mode and receives a server-issued, isolated demo identity/workspace with strict quotas and expiry.
2. Visitor may register/sign in using configured OAuth providers (Google and GitHub). OAuth state and callback validation are mandatory.
3. An authenticated customer receives a personal workspace, separate from all other users and from the company workspace.
4. GitHub repository access is separately authorized and scoped to the repositories the customer selects.
5. Paid features are enabled only after a verified payment-provider webhook or server-side payment verification. Browser redirects alone never grant access.
6. The Owner App requires an explicitly provisioned owner identity. Public registration and payment can never grant owner privileges.
7. Logout revokes the session. Session cookies are HTTP-only, Secure in production, SameSite-protected, and rotated after login.

## Owner App responsibilities

- Customer/account and workspace status
- Demo-to-paid conversion and subscription/payment status
- Mission queue, completion/failure rates, and factory health
- AI usage, quotas, infrastructure usage, and operating cost estimates
- Product errors, test/QA outcomes, and security/audit events
- Plan and feature configuration
- Company-owned projects and company workspace controls

Owner-only data must never be returned by customer endpoints. Owner actions that change access, billing, or factory configuration must be auditable.

## Delivery phases

### Phase 1 — identity and workspace foundation
- Add persisted user identities and sessions with a documented migration.
- Add explicit workspace types (company, personal, demo) and membership/ownership records.
- Add server-side authentication/authorization dependencies and tests for unauthenticated, cross-user, and non-owner access.
- Define a safe owner bootstrap process through deployment configuration; never use a public signup flag.

### Phase 2 — OAuth and customer entry
- Implement Google and GitHub sign-in with configured callback URLs and OAuth state validation.
- Add login/logout/account UI and protected customer routes.
- Keep GitHub repo authorization separate from sign-in.

### Phase 3 — real workspace isolation
- Scope mission, project, generated output, memory, and provider connection reads/writes by workspace on the server.
- Move from the current singleton company control center to workspace-scoped execution, or isolate per-workspace runners with explicit resource limits.
- Ensure existing company data remains in the company workspace during migration.

### Phase 4 — demo mode
- Add anonymous/temporary demo workspaces with expiry, per-IP/session protections, build quotas, runtime limits, and bounded AI usage.
- Ensure demo runs cannot publish to repositories or access secrets by default.
- Add an upgrade path that preserves only explicitly transferable user-owned data.

### Phase 5 — payments and entitlements
- Add plans, subscriptions/one-time purchases as configured, verified payment webhooks, idempotency, and entitlement checks.
- Never unlock paid access based only on a client redirect or a user-editable value.

### Phase 6 — owner-only app
- Add owner dashboard and owner-protected APIs for business metrics, customers, billing, factory monitoring, usage, and audit logs.
- Make the owner identity independently provisioned and test that customers cannot obtain owner access.

## Release gates

- Tests cover login/session expiry, OAuth state mismatch, demo quotas, payment webhook replay, owner authorization, and cross-workspace access.
- Customer A cannot list/read/change Customer B's data.
- Customer requests cannot access company data or owner endpoints.
- Demo users cannot bypass limits by changing request payloads or creating new mission IDs.
- OAuth/payment secrets are absent from source control and browser responses.
- Deployment configuration, callback URLs, database migrations, backups, and rollback steps are documented.
- Do not call the platform production-ready until these gates are implemented and verified.
