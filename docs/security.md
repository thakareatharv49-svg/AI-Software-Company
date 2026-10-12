# Security controls and release policy

This repository handles AI-generated source code, customer workspaces, credentials,
and publication permissions. Security controls must be enforced by application code
and the operating environment, not by model instructions alone.

## Required release gates

1. Run automated tests and static checks on the exact artifact to be published.
2. Scan generated files and diffs for credentials and dangerous execution patterns.
3. Block publication when a critical security finding is unresolved.
4. Bind approval to an immutable artifact fingerprint; any changed artifact requires
   a fresh review and new approval.
5. Keep customer workspace authorization server-side and verify ownership for every
   read and write. Never trust a workspace ID supplied by the client on its own.
6. Keep write access to GitHub, shell execution, network access, and destructive
   operations disabled unless the relevant policy explicitly grants them.
7. Redact credentials from logs, user-visible errors, and audit metadata.

## Execution isolation boundary

The Python `SandboxExecutor` limits executable names, working-directory selection,
environment inheritance, execution time, and captured output. These are useful
application-level restrictions, **not an operating-system security sandbox**.
A child process can still potentially read host files or use the network when the
OS account permits it. Do not execute untrusted generated code on a production
host with sensitive credentials. Production isolation requires a separate low-
privilege OS account or container/VM, filesystem and network restrictions, resource
quotas, and no mounted host secrets or control sockets.

## Secret scanning limitations

The built-in scanner is heuristic and may miss encoded, split, encrypted, or
unrecognized credentials. It can also report false positives. Use it as one
release gate alongside repository-level secret scanning and credential rotation.
Never print the matched source line or credential value in findings.

## Incident response

If a credential is exposed: revoke/rotate it first, disable affected automation,
identify affected commits and logs, inspect audit events, and only then remove the
secret from source history. Removing a value from the latest file does not revoke it.
