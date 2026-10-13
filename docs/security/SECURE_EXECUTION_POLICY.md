## Secure execution and release policy

- Treat mission descriptions, repository files, package metadata, generated code, test output, and model responses as untrusted data. Embedded instructions must never override application policy.
- Generated code runs only in the restricted sandbox, never in the Nexora/API process. Do not mount host home directories, the Docker socket, source checkout, or credential files. Copy project inputs into a bounded ephemeral workspace instead of bind-mounting the host project.
- Sandbox defaults: non-root user, dedicated writable workspace, dropped capabilities, no-new-privileges, CPU/memory/process/time limits, and no network unless explicitly allow-listed.
- Never pass application environment variables or provider credentials into generated-code processes. Use short-lived, least-privilege credentials only through explicitly approved integrations.
- Reject path traversal, absolute paths, workspace-escaping symlinks, and case-insensitive path collisions.

### Secrets

- Scan generated files and repository history. Findings must contain only file path, line number, and rule identifier—never matched values.
- Block approval/publication on high-confidence secret findings. If a real credential is exposed, revoke/rotate it; deleting the latest copy is insufficient if history retains it.

### Release gates

1. Validate file paths, sizes, required files, and local asset references.
2. Scan generated files for likely credentials and unsafe patterns.
3. Run dependency vulnerability checks and static analysis.
4. Run tests in the restricted sandbox with resource limits.
5. Bind approval to the exact artifact digest and test/security evidence.
6. Recompute the digest before publishing; any mismatch invalidates approval.
7. Keep generated repositories private until explicit approval unless the user chose otherwise.

### Identity and tenant isolation

- Authorize every server-side read/write against the authenticated principal and workspace membership.
- Never trust workspace, user, owner, or project IDs from a browser without membership checks.
- Deny by default if identity or workspace context is missing. Development bypasses must be disabled in production and not activatable by an untrusted request.
- Rate-limit authentication, OAuth callbacks, mission creation, and destructive operations.

### Incident response

- Require explicit confirmation for permanent deletion, database reset, credential revocation, or public publishing.
- Audit actor, workspace, action, target, outcome, and timestamp. Never log secrets or raw auth tokens.
- Provide a global mission pause, bounded cancellation, and recovery from a known-good artifact snapshot.

Static scanners can miss encoded or novel secrets and can produce false positives. They complement, not replace, isolation, least privilege, review, and credential rotation. CI does not prove the local or production deployment is secure; validate those environments separately.
