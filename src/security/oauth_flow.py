"""Small OAuth security primitives shared by provider login adapters.

Callers must persist the returned state and verifier server-side for a short
lifetime, bind them to the initiating browser, and consume them exactly once.
These helpers do not implement an OAuth callback or authenticate a user.
"""
from __future__ import annotations

import base64
import hashlib
import secrets


def issue_oauth_state() -> str:
    """Create an unpredictable anti-CSRF OAuth state value."""
    return secrets.token_urlsafe(32)


def issue_pkce_verifier() -> str:
    """Create a high-entropy PKCE verifier suitable for S256 challenges."""
    return secrets.token_urlsafe(48)


def pkce_s256_challenge(verifier: str) -> str:
    """Derive the RFC 7636 S256 challenge for an issued verifier."""
    if not isinstance(verifier, str) or not 43 <= len(verifier) <= 128:
        raise ValueError("PKCE verifier must be between 43 and 128 characters")
    try:
        verifier_bytes = verifier.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("PKCE verifier must contain ASCII characters only") from exc
    digest = hashlib.sha256(verifier_bytes).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
