# M95–M100 — Product Quality and Release Acceptance Gates

## Scope

This increment provides deterministic, evidence-consuming decision helpers. It does not pretend to execute a browser, run a security scanner, deploy a product, or provide real-factory soak evidence. The caller must supply actual evidence from those systems.

## Gate chain

1. **M95 product review:** require complete requirement coverage, passing automated/security/responsive/accessibility checks, unique finding IDs, and no unresolved critical/high findings.
2. **M96 release integrity:** candidate revision must equal tested revision; quality and security gates must pass; required approval must be present, especially for external publication.
3. **M97 multi-mission soak:** expected and actual mission IDs must match exactly; duplicate outcomes, unexplained non-success outcomes, cross-mission leakage, false success, and starvation block acceptance.
4. **M98 improvement regression:** compare quality, safety, latency, and cost against a baseline; reject regressions outside configured thresholds.
5. **M99 controlled rollout preflight:** reuse exact-revision release readiness and approval checks before any external rollout. Actual rollout and rollback remain owned by the deployment subsystem.
6. **M100 integrated acceptance:** combine quality, release, soak, and improvement decisions while preserving gate-specific reasons.

## Safety and limitations

- A passed decision means supplied evidence satisfies these deterministic rules; it does not independently authenticate the evidence source.
- These helpers do not replace the factory worker, browser QA, security scanner, approval service, or deployment controller.
- The integrated gate must only be invoked with evidence generated for the same candidate revision. Real factory-path validation remains required.
- Do not mark the milestones complete until exact-head CI and real factory integration/acceptance evidence pass.
