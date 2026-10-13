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
- M48, PR #332: validate factory execution timeouts — merged. Merge commit: `bbabe0eb509c9d5772e7efa15ba2caa234774035`. Rejects zero, negative, infinite, and NaN timeout configuration before dequeueing a mission; regression tests assert queue/attempt state is unchanged.
- M49, PR #333: reject invalid factory timeout types — merged. Merge commit: `453fe63fd1b0cdff6d20bb507775508ad5fd8b63`. Extends timeout validation to reject booleans and non-numeric values with a stable `ValueError`, with regression coverage for `None`, strings, and booleans.
- M50, PR #334: validate factory stage budgets — open; head `4b21c1267822824e4d3cc9ddb20f92f1bf87d028`. Rejects negative, float, string, and boolean `max_stages` values before dequeuing; `None` and non-negative integers remain valid.

## Open reliability work to resume
- PR #313, M40: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/313
  - Branch: `fix/recover-orphaned-continuous-missions`; head `b53a7f48caf8b8291a4f64de1f381a3cb1c7708d`; base `main`.
  - Recovers durable RUNNING jobs to QUEUED after continuous factory worker exceptions, synchronizes durable job and in-memory queue, saves snapshot, and emits a sanitized error event.
  - Secret scan, dependency audit, and CodeQL succeeded. CI run `38471192694` was still in progress at the last check, in the Tests step. Older CI run `38469943049` was also still in progress. Do not merge until current required checks complete successfully; investigate if tests fail or remain stuck.
- PR #332, M48: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/332 — merged; merge commit `bbabe0eb509c9d5772e7efa15ba2caa234774035`.
- PR #333, M49: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/333 — merged; merge commit `453fe63fd1b0cdff6d20bb507775508ad5fd8b63`.
- PR #334, M50: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/334
  - Branch: `fix/validate-factory-stage-budget`; base `main`; head `4b21c1267822824e4d3cc9ddb20f92f1bf87d028`.
  - Validates `max_stages` before any queue mutation; rejects malformed values and verifies queue/attempt state remains unchanged. Wait for all required workflows on current head before merging.
- PR #314, M41: https://github.com/thakareatharv49-svg/AI-Software-Company/pull/314
  - Branch: `test/factory-continues-after-persistence-error`; head `67429f0cef113fc5873f482957a0bfdc1831e999`; base `fix/recover-orphaned-continuous-missions` (stacked on PR #313).
  - Tests that one mission's snapshot-save failure is safely handled and the next queued mission can complete.
  - CI run `38470664447` was still in progress at the last check; test step was pending.
  - Merge #313 first after checks pass, then retarget #314 to `main`, inspect its diff and current head, rerun/verify required checks, and merge only when all required checks pass.

## Last verified check state (2026-10-14)
- PR #330 current head `c130d406fa02d99961f500e3f28ad85ecf1609aa`: CI, Secret and Credential Scan, Dependency Vulnerability Audit, CodeQL all succeeded; merged.
- PR #331 current head `b2b35f4cabff287f1dbd7b51fa4729712fc4cd6e`: CI, Secret and Credential Scan, Dependency Vulnerability Audit, CodeQL all succeeded; merged.
- PR #313 and #314 remain older open factory-recovery PRs; their CI test jobs have been unusually long-running, so re-query live GitHub state and logs before acting. PR #334 is the active M50 validation PR.
- Last checked CI job for #313: `115550386017`; Tests was running at the last check.
- Last checked CI job for #314: `115548570695`; Tests was pending at the last check.
- M48 PR #332 CI, secret scan, dependency audit, and both CodeQL analyses passed on head `2f23f2a6353e39833b92175a1970f8d6701681d0`; merged successfully.
- M49 PR #333 CI, secret scan, dependency audit, and both CodeQL analyses passed on head `432854bbfd291bcad4c48fd16e85992066b1ff9c`; merged successfully.

## Working rules
1. Start each resumed session by checking live GitHub PR state, exact head SHA, workflow runs, and dependency/base-branch relationships.
2. Fix failures rather than asking the user to merge or resolve routine CI problems.
3. Merge sequentially when dependencies exist; use squash merge and expected-head-SHA protection.
4. Do not merge while any required workflow is pending, in progress, or failed.
5. After merging a stacked PR, update its base to `main`, re-inspect changes, and ensure CI validates the final PR state.
6. Update this context file as milestones and PR status change, so future sessions can resume from repository documentation rather than chat history.
