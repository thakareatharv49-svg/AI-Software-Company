# Security controls and release policy

This repository handles AI-generated source code, customer workspaces, credentials,
and publication permissions. Security controls must be enforced by application code
and the operating environment, not by model instructions alone.

## Required release gates

1. Run automated tests and static checks on the exact artifact to be published.
2. Scan generated files and diffs for credentials and dangerous execution patterns.
3. Block publication when a critical/high security finding is unresolved.
4. Bind approval to an immutable artifact fingerprint; any changed artifact requires
   a fresh review and new approval.
5. Keep customer workspace authorization server-side and verify ownership for every
   read and write. Never trust a workspace ID supplied by the client on its own.
6. Keep GitHub writes and destructive operations disabled unless policy explicitly
   grants them. Untrusted code must not receive host credentials.
7. Redact credentials from logs, user-visible errors, and audit metadata.

## Generated-code execution

Development and production default to `SANDBOX_MODE=container`. Host execution is not a
security boundary and is only an explicit local-development exception. Production/staging
configuration validation requires `SANDBOX_MODE=container`; startup refuses unsafe host mode. Build the reviewed runtime
image with `docker build -t ai-software-company-sandbox:latest docker/sandbox`.

The container backend runs with no network, a read-only root filesystem, dropped Linux
capabilities, no-new-privileges, process/memory/CPU/file-descriptor limits, bounded output,
and a 512 MiB ephemeral workspace. The project workspace is copied into that temporary
filesystem; it is not mounted into the container, so generated code cannot read sibling host
files, mutate the approved host artifact during QA, or fill the host workspace. The container
does not inherit host environment variables or mount the Docker socket. Docker must be
available and the image must already exist; the runner does not pull arbitrary images. If
Docker is unavailable or staging fails, isolated execution fails closed.

The sandbox image provides Python, pytest, and Node for basic generated-app checks. Projects
that need extra dependencies require a separate controlled dependency/build stage; do not
solve that by mounting host virtual environments or enabling unrestricted network access.

## Secret scanning limitations

The built-in scanner is heuristic and may miss encoded, split, encrypted, or unrecognized
credentials. It can also report false positives. Use it as one release gate alongside
repository-level scanning and credential rotation. Never print the matched source line or
credential value in findings.

## Incident response

Follow the detailed [Security Operations and Incident Response Runbook](security/SECURITY_OPERATIONS_RUNBOOK.md).
If a credential is exposed, revoke/rotate it first, disable affected automation, identify
affected commits and logs, inspect audit events, and only then remove the secret from
source history. Removing a value from the latest file does not revoke it.

## Emergency factory pause

The owner-only `POST /api/factory/pause` endpoint blocks new submissions, retries,
queue launches, and continuous-mode restarts. It deliberately lets a currently running
project finish rather than cancelling an async worker unsafely. Use
`POST /api/factory/resume` to release the pause. The current pause flag is process-local;
set `FACTORY_START_PAUSED=true` to require an explicit resume after startup. Multi-worker
deployments should use a shared durable control-state store and enforce the pause at every
worker before enabling customer traffic.
