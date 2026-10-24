# M86 — Large-project benchmark runner

Status: **IN PROGRESS**. The runner is implemented, but the milestone is not complete until all three cases have been run through the real factory and the recorded evidence reviewed.

## Run it

Start the AI Software Company API with the factory configured, then run from the repository root:

```powershell
python scripts/run_m86_large_project_benchmark.py
```

Select a subset while debugging:

```powershell
python scripts/run_m86_large_project_benchmark.py --case cli-utility
```

For a non-default API address, set `AI_SOFTWARE_COMPANY_URL` or pass `--base-url`. For authenticated environments, provide `AI_SOFTWARE_COMPANY_BEARER_TOKEN` or `AI_SOFTWARE_COMPANY_AUTH_COOKIE` in the process environment. Do not put credentials in the catalog, command line, result file, or repository. The runner does not turn on continuous mode, publish repositories, or approve releases.

Default catalog: `tests/fixtures/large_project_benchmark_cases.json`. Default evidence file: `artifacts/m86-large-project-benchmark-results.json` (ignored build output; commit a reviewed baseline separately if needed).

## What the runner records

For each case it submits the fixture mission to `POST /api/missions`, runs it via `POST /api/missions/{id}/factory-run`, then gathers the durable job, diagnostics, audit count, and output manifests from the factory API. It records elapsed time, retry count when exposed by the job record, stage status/error details, actual QA fields available on the mission plan, generated workspace file paths, and check-level pass/fail diagnostics.

The acceptance checks include:
- `factory_terminal_success`: the real mission reached completed state.
- `artifact_safety`: generated workspace files pass the repository's artifact validator.
- `required_files`: every fixture-required file exists.
- `required_features`: a deliberately simple textual marker heuristic, useful for triage but not proof of semantic correctness.
- `test_command_exit_code`: actual persisted QA exit-code evidence is zero; missing evidence fails closed.

## Interpretation and limitations

The runner returns a non-zero exit code if any case/check fails and writes the complete JSON report even when an individual case fails. A missing workspace, absent QA exit code, API error, timeout, or missing required file is a recorded failure, not a pass. Generated file names and textual feature markers are diagnostic only; reviewers must inspect the real application and test evidence. The current factory's synchronous factory-run API can block until a mission finishes, so the configured per-mission deadline currently bounds polling but cannot interrupt a blocked HTTP request; the HTTP request timeout remains separately bounded.

The default run uses the configured model/runtime, so it is a real factory-path evaluation rather than a deterministic fake. It may consume local compute or provider quota and may expose current generator limitations. Provider-dependent execution must not be made a required unit-test/CI step. Unit tests cover runner contracts and failure reporting without calling a live model.

## M86 exit gate

1. Runner contract/unit tests and the full CI/security workflows pass on the exact PR head.
2. Execute the web, API, and CLI cases through the real factory in a configured environment.
3. Save and review the actual JSON evidence for all cases; do not substitute fixture-only results.
4. Investigate failures and record a reproducible baseline. A failing product case is useful evidence, but M86 is not complete until the baseline clearly identifies its stage/check failure and the acceptance gate is agreed as met.
