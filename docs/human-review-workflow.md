# Human review, revisions, and release approval

The product lifecycle is intended to be human-directed:

1. Generate a product and run automated QA and security checks.
2. Prepare a review with explicit acceptance requirements and verification evidence.
3. Let the owner inspect the product and mark requirements as passed or failed.
4. If unsatisfied, submit concrete feedback; the next revision must preserve existing requirements and retest regressions.
5. Approve only when every acceptance requirement is verified and automated QA/security gates pass.
6. Publish the approved revision to GitHub and record the repository URL.

## Domain lifecycle

`draft -> in_review -> approved -> published`

A review can move from `in_review` to `changes_requested`, then return to `in_review` after the revised product is tested. A revision clears any prior approval/publication metadata. Publication must be rejected unless the current revision is approved.

## Quality and safety invariants

- A review cannot be submitted without requirements or passing QA and security checks.
- Approval is rejected while any requirement is pending or failed.
- Feedback must be non-empty and increments the revision counter.
- Publication is a separate action from approval and must be recorded only after the GitHub operation succeeds.
- Approval never overrides a failing quality or security gate.

The domain contract and transition tests are the first implementation slice. API/UI integration, durable review storage, and routing all generated GitHub writes through the approval gate are follow-on integration work; they must be completed before this workflow is considered fully available in the control center.
