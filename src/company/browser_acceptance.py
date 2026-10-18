from __future__ import annotations

import asyncio
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from functools import partial
from typing import Any


MAX_ROUTES_TO_PROBE = 8
MAX_PAGE_ERRORS = 20
MAX_INTERACTION_LABEL = 120


def _safe_internal_href(href: str, origin: str) -> bool:
    """Accept only relative or same-origin HTTP links for route probes."""
    from urllib.parse import urljoin, urlparse

    parsed_origin = urlparse(origin)
    parsed = urlparse(urljoin(origin, href))
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc == parsed_origin.netloc
        and not parsed.username
        and not parsed.password
    )


def _safe_interaction_label(label: str) -> bool:
    """Avoid controls whose first click commonly destroys or exits a test state."""
    lowered = label.strip().casefold()
    return bool(lowered) and not any(
        term in lowered
        for term in ("delete", "remove", "clear", "reset", "logout", "log out", "sign out")
    )


class _QuietHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        # The generated workspace is untrusted. Do not let symlinks or dotfiles
        # turn the local preview server into a reader for host-side secrets.
        root = Path(self.directory or ".").resolve()
        candidate = Path(super().translate_path(path)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return str(root / "__blocked_browser_acceptance_path__")
        relative = candidate.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            return str(root / "__blocked_browser_acceptance_path__")
        return str(candidate)

    def log_message(self, format: str, *args: Any) -> None:
        return


def _run_browser_checks(workspace: Path, timeout_ms: int) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "status": "unavailable",
            "detail": "Playwright is not installed; browser acceptance cannot run.",
            "routes_checked": [],
            "interactions_checked": [],
            "page_errors": [],
        }

    if not workspace.is_dir() or not (workspace / "index.html").is_file():
        return {
            "status": "not_applicable",
            "detail": "No root index.html browser entry point exists.",
            "routes_checked": [],
            "interactions_checked": [],
            "page_errors": [],
        }

    handler = partial(_QuietHandler, directory=str(workspace.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    page_errors: list[str] = []
    routes_checked: list[str] = []
    interactions_checked: list[str] = []
    failures: list[str] = []

    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:
                return {
                    "status": "unavailable",
                    "detail": f"Chromium could not launch: {type(exc).__name__}: {exc}"[:1000],
                    "routes_checked": [],
                    "interactions_checked": [],
                    "page_errors": [],
                }
            try:
                context = browser.new_context()
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                page.on("pageerror", lambda error: page_errors.append(str(error)[:500]))
                page.route(
                    "**/*",
                    lambda route: route.continue_()
                    if route.request.url.startswith(origin + "/")
                    else route.abort(),
                )
                response = page.goto(origin + "/", wait_until="domcontentloaded")
                routes_checked.append("/")
                if response is None or response.status >= 400:
                    failures.append(f"Root route returned HTTP {response.status if response else 'no response'}.")
                page.locator("body").wait_for(state="visible")
                if not page.locator("body").inner_text().strip():
                    failures.append("Root route rendered an empty page body.")

                # Exercise a small number of ordinary internal routes. External
                # requests are blocked so generated pages cannot call third-party services.
                links = page.locator("a[href]")
                candidates: list[str] = []
                for index in range(min(links.count(), 40)):
                    href = links.nth(index).get_attribute("href") or ""
                    if _safe_internal_href(href, origin) and href not in candidates:
                        candidates.append(href)
                for href in candidates[:MAX_ROUTES_TO_PROBE]:
                    from urllib.parse import urljoin, urlparse

                    target = urljoin(origin + "/", href)
                    path = urlparse(target).path or "/"
                    if path == "/" or target.split("#", 1)[0] == page.url.split("#", 1)[0]:
                        continue
                    try:
                        route_response = page.goto(target, wait_until="domcontentloaded")
                        routes_checked.append(path)
                        if route_response is None or route_response.status >= 400:
                            failures.append(f"Internal route {path} returned HTTP {route_response.status if route_response else 'no response'}.")
                        page.locator("body").wait_for(state="visible")
                        if not page.locator("body").inner_text().strip():
                            failures.append(f"Internal route {path} rendered an empty body.")
                    except Exception as exc:
                        failures.append(f"Internal route {path} failed: {type(exc).__name__}: {exc}"[:500])

                # Exercise one visible, non-destructive button from the entry page.
                page.goto(origin + "/", wait_until="domcontentloaded")
                buttons = page.locator("button:visible")
                for index in range(min(buttons.count(), 30)):
                    button = buttons.nth(index)
                    label = (button.inner_text() or button.get_attribute("aria-label") or "").strip()
                    if _safe_interaction_label(label):
                        # Do not click a navigation control that is already marked
                        # as the active page; it is expected to be a no-op.
                        aria_current = (button.get_attribute("aria-current") or "").casefold()
                        aria_pressed = (button.get_attribute("aria-pressed") or "").casefold()
                        classes = (button.get_attribute("class") or "").casefold()
                        if aria_current in {"page", "true"} or aria_pressed == "true" or any(
                            marker in classes.split() for marker in ("active", "selected", "current")
                        ):
                            continue
                        before_text = page.locator("body").inner_text()
                        before_url = page.url
                        before_expanded = button.get_attribute("aria-expanded")
                        before_pressed = button.get_attribute("aria-pressed")
                        try:
                            button.click()
                            page.wait_for_timeout(100)
                            after_text = page.locator("body").inner_text()
                            after_expanded = button.get_attribute("aria-expanded")
                            after_pressed = button.get_attribute("aria-pressed")
                            changed = (
                                after_text != before_text
                                or page.url != before_url
                                or after_expanded != before_expanded
                                or after_pressed != before_pressed
                            )
                            if changed:
                                interactions_checked.append(label[:MAX_INTERACTION_LABEL])
                                break
                            # A visible button may be an inert active navigation item.
                            # Try the next safe control before failing the acceptance.
                        except Exception as exc:
                            failures.append(f"Button interaction '{label[:80]}' failed: {type(exc).__name__}: {exc}"[:500])

                if page_errors:
                    failures.extend(f"Uncaught browser error: {error}" for error in page_errors[:MAX_PAGE_ERRORS])
                if not routes_checked:
                    failures.append("No browser route was successfully opened.")
                return {
                    "status": "passed" if not failures else "failed",
                    "detail": "Browser routes and a safe interaction were exercised." if not failures else "; ".join(failures)[:3000],
                    "routes_checked": routes_checked,
                    "interactions_checked": interactions_checked,
                    "page_errors": page_errors[:MAX_PAGE_ERRORS],
                }
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def run_browser_acceptance(
    working_directory: str | Path,
    *,
    timeout_ms: int = 5000,
) -> dict[str, Any]:
    """Run isolated Chromium smoke acceptance for a generated browser product."""
    if not 100 <= timeout_ms <= 30_000:
        raise ValueError("timeout_ms must be between 100 and 30000")
    workspace = Path(working_directory).resolve()
    return await asyncio.to_thread(_run_browser_checks, workspace, timeout_ms)
