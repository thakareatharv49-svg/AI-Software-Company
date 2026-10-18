# R6: evidence-based completion gate

A mission may be marked accepted only when its completion report is backed by execution evidence. Generated files, a successful model response, or a QA status label alone are not sufficient.

## Required evidence

- All autonomous lifecycle stages required by `AutonomousCompanyAcceptance` completed.
- The QA runner explicitly reports `passed` and an integer exit code of exactly `0`.
- The pipeline's per-command QA ledger is present, non-empty, and every record has status `passed` plus integer exit code `0`. Missing, malformed, skipped-without-a-record, or failed evidence blocks completion.
- Code/security review is approved.
- App-like browser products have a root browser preview and recorded browser acceptance with status `passed`. A preview file alone is not behavioral proof.
- Deployment, monitoring, and learning requirements continue to be checked separately.

The final acceptance report names each failed check. The factory runner records those failures against the corresponding mission stages before it raises, so the mission cannot silently become completed after a failed gate.

## Validation

Focused regression tests:

```powershell
python -m pytest tests/unit/company/test_acceptance.py -q
```

Related factory evidence tests:

```powershell
python -m pytest tests/unit/company/test_factory_qa_evidence.py -q
```

The command ledger and browser acceptance evidence are produced by the R4 and R5 pipeline improvements respectively. Until those evidence producers are present, the gate intentionally fails closed for products that lack the required evidence.
