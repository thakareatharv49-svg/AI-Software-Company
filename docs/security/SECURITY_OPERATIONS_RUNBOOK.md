# Security Operations and Incident Response Runbook

This runbook is for the Nexora / AI Software Company operator. Use it when a generated
project behaves unexpectedly, a credential may have leaked, a customer workspace may
have been accessed incorrectly, or an unsafe artifact is about to be published.

## 1. Contain first

1. Pause the factory from the authenticated control center. Do not submit more missions.
2. Cancel affected queued missions and stop any unsafe work using the supported control-center controls.
3. Set `GITHUB_ALLOW_WRITES=false` and restart the service if publication risk exists.
4. Do not approve or publish any artifact while an incident is open.
5. Preserve sanitized audit entries, mission IDs, artifact digests, timestamps, and CI links.
   Do not copy raw tokens, passwords, or private keys into incident notes.

The factory pause is process-local in the current deployment. In a multi-worker deployment,
pause every worker and do not accept customer traffic until shared durable pause state is
implemented and verified.

## 2. If a credential may have leaked

1. Revoke or rotate the credential at its issuing provider immediately.
2. Rotate dependent credentials if the exposed secret could unlock them.
3. Disable the affected integration until the replacement secret is stored server-side.
4. Identify affected repositories, commits, logs, audit events, and generated artifacts.
5. Remove the secret from files and, if committed, follow the provider's repository-history
   cleanup procedure. History cleanup does not replace revocation.
6. Run secret scanning again and confirm the old credential no longer works.

Never paste a live credential into a GitHub issue, pull request, model prompt, or incident
report. Use fake values in regression tests.

## 3. If generated code may be unsafe

1. Keep the artifact unpublished and pause the factory.
2. Record the mission ID, artifact digest, source branch, test results, and security findings.
3. Verify that the run used `SANDBOX_MODE=container` and the reviewed non-root sandbox image.
4. Inspect generated files, dependency manifests, install scripts, test output, and network
   behavior. Treat README files and tool output as untrusted input.
5. Do not rerun the artifact on the host to investigate it. Reproduce only in the restricted
   sandbox with bounded resources and no network.
6. Restore the last known-good reviewed artifact if recovery is required.

## 4. If workspace isolation or authorization is suspect

1. Pause customer-facing operations and disable publication.
2. Record affected user and workspace IDs in access-controlled incident notes.
3. Review server-side authorization decisions and sanitized audit events.
4. Check project, mission, artifact, and repository ownership for cross-workspace references.
5. Do not disclose another customer's data while investigating; return a generic not-found
   response to unauthorized requests.
6. Add a regression test reproducing the exact authorization failure before re-enabling access.

## 5. Safe recovery and re-enable checklist

- [ ] The root cause is understood and a fix is merged with passing CI and security checks.
- [ ] Any exposed credentials have been revoked and replaced.
- [ ] The artifact is restored from a known-good commit or regenerated in the restricted sandbox.
- [ ] Secret scanning, dependency audit, static analysis, and product tests pass.
- [ ] The final artifact digest matches the reviewed artifact.
- [ ] A human explicitly approves publication of that exact artifact.
- [ ] GitHub write access is re-enabled only if needed.
- [ ] The factory is resumed deliberately and one small, monitored mission is observed end to end.

## 6. Local sandbox setup

For a new checkout, copy `.env.example`, then build the sandbox image:

```powershell
docker build -t ai-software-company-sandbox:latest docker/sandbox
```

For an existing checkout, remember that `.env` overrides application defaults. Set
`SANDBOX_MODE=container` and restart the service. `SANDBOX_MODE=host` is not OS isolation
and must only be used as a deliberate local-development exception. Do not mount your home
directory, credentials, source checkout, or Docker socket into generated-code containers.

## 7. Known operational limitation

A passing CI run validates repository code and tests; it does not prove Docker Desktop,
the local Ollama runtime, the production network, or deployment secrets are configured
safely. Before exposing Nexora to customers, run a controlled acceptance test in the actual
deployment environment and verify isolation, authorization, cancellation, recovery, and
approval-gated publication.
