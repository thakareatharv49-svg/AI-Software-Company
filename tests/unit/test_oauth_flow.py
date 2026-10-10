import re

import pytest

from src.security.oauth_flow import (
    issue_oauth_state,
    issue_pkce_verifier,
    pkce_s256_challenge,
)


def test_oauth_state_is_unpredictable_url_safe_text() -> None:
    first = issue_oauth_state()
    second = issue_oauth_state()

    assert first != second
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first)


def test_pkce_verifier_and_challenge_follow_s256_shape() -> None:
    verifier = issue_pkce_verifier()
    challenge = pkce_s256_challenge(verifier)

    assert 43 <= len(verifier) <= 128
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", challenge)


@pytest.mark.parametrize("verifier", ["", "short", "x" * 129, "é" * 50])
def test_pkce_rejects_invalid_verifiers(verifier: str) -> None:
    with pytest.raises(ValueError):
        pkce_s256_challenge(verifier)
