

## R5: Browser acceptance for web products

When a generated product includes a root `index.html`, the pipeline launches it in headless Chromium from an isolated local HTTP server before artifact validation, security review, and release. The browser probe:

- Opens the root route and checks for a successful response and non-empty visible page.
- Discovers and probes up to eight same-origin internal links.
- Exercises one visible non-destructive button when available.
- Captures uncaught browser page errors.
- Blocks requests to external origins during the acceptance run.

Browser acceptance evidence (status, probed routes, interaction labels, and bounded diagnostics) is retained in mission QA evidence. A failed or unavailable browser run blocks delivery rather than being reported as a pass. CI installs Playwright's Chromium browser so the integration test runs against a real browser; the integration test may skip in developer environments where Chromium is not installed.
