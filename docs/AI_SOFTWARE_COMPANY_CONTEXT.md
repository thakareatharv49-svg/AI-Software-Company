# AI Software Company — Durable Project Context

Last updated: 2026-10-14

## Product direction
- Repository: https://github.com/thakareatharv49-svg/AI-Software-Company
- Build an autonomous AI software company/project factory that plans, builds, tests, reviews, and delivers substantial projects continuously—not only tiny demos.
- HQ product/system name: **Nexora**. The generated software-company product branding remains **AI Software Company**.
- User expects milestone-by-milestone progress, with checks, fixes, and merges handled by the assistant. Never report a PR merged unless GitHub confirms it. Merge only after required CI and security checks succeed on the exact current PR head SHA.
- Important quality goal: improve reliability of larger missions (including Notes/Expense Tracker), retries, queue continuity, safe persistence, and reviewable product output before final publishing.
- Do not overwrite or discard generated product artifacts such as `generated-products/` during local work.

## Recently completed milestones
- M45, PR #329: normalize restored factory counters — merged.
- M46, PR #330: tolerate factory snapshot-store outages — merged after all four required workflows passed on head `c130d406fa02d99961f500e3f28ad85ecf1609aa`. Merge commit: `509feb05ba5fb2ed091a8b1b4541c7b06c18ae95`.
- M47, PR #331: validate factory retry budgets — merged after all four required workflows passed on head `b2b35f4cabff287f1dbd7b51fa4729712fc4cd6e`. Merge commit: `929015fa30afa827528405d2bbc6c831b0889acf`.
- M48, PR #332: validate factory execution timeouts — open; head `2f23f2a6353e39833b92175a1970f8d6701681d0`; rejects zero, negative, infinite, and NaN timeout configuration before dequeueing a mission, with regression tests that assert the queue/attempt state is unchanged.

## Open reliability work to resume
- PR #313, M40: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/313
  - Branch: `fix/recover-orphaned-continuous-missions`; head `b53a7f48caf8b8291a4f64de1f381a3cb1c7708d`; base `main`.
  - Recovers durable RUNNING jobs to QUEUED after continuous factory worker exceptions, synchronizes durable job and in-memory queue, saves snapshot, and emits a sanitized error event.
  - Secret scan, dependency audit, and CodeQL succeeded. CI run `38471192694` was still in progress at the last check, in the Tests step. Older CI run `38469943049` was also still in progress. Do not merge until current required checks complete successfully; investigate if tests fail or remain stuck.
- PR #332, M48: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/332
  - Branch: `fix/validate-factory-execution-timeout`; base `main`; head `2f23f2a6353e39833b92175a1970f8d6701681d0`.
  - Required CI, secret scan, dependency audit, and CodeQL were still running/queued at the last check. Do not merge until all required workflows pass on the exact current head SHA.
- PR #314, M41: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/314
  - Branch: `test/factory-continues-after-persistence-error`; head `67429f0cef113fc5873f482957a0bfdc1831e999`; base `fix/recover-orphaned-continuous-missions` (stacked on PR #313).
  - Tests that one mission's snapshot-save failure is safely handled and the next queued mission can complete.
  - CI run `38470664447` was still in progress at the last check; test step was pending.
  - Merge #313 first after checks pass, then retarget #314 to `main`, inspect its diff and current head, rerun/verify required checks, and merge only when all required checks pass.

## Last verified check state (2026-10-14)
- PR #330 current head `c130d406fa02d99961f500e3f28ad85ecf1609aa`: CI, Secret and Credential Scan, Dependency Vulnerability Audit, CodeQL all succeeded; merged.
- PR #331 current head `b2b35f4cabff287f1dbd7b51fa4729712fc4cd6e`: CI, Secret and Credential Scan, Dependency Vulnerability Audit, CodeQL all succeeded; merged.
- PR #313 and #314 are the known remaining open PRs; re-query live GitHub state before acting because statuses may have changed.
- Last checked CI job for #313: `115550386017`; Tests was running.
- Last checked CI job for #314: `115548570695`; Tests was pending.

## Working rules
1. Start each resumed session by checking live GitHub PR state, exact head SHA, workflow runs, and dependency/base-branch relationships.
2. Fix failures rather than asking the user to merge or resolve routine CI problems.
3. Merge sequentially when dependencies exist; use squash merge and expected-head-SHA protection.
4. Do not merge while any required workflow is pending, in progress, or failed.
5. After merging a stacked PR, update its base to `main`, re-inspect changes, and ensure CI validates the final PR state.
6. Update this context file as milestones and PR status change, so future sessions can resume from repository documentation rather than chat history.
