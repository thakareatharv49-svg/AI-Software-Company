"""OAuth sign-in and opaque server-side session issuance.

Provider access tokens are used only for the callback profile request and are
never persisted. Provider identities are not auto-linked by email.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.db.models.identity import AuthSessionModel, OAuthIdentityModel
from src.db.models.user import UserModel
from src.db.models.workspace import WorkspaceMembershipModel, WorkspaceModel
from src.db.session import get_db
from src.security.oauth_flow import issue_oauth_state, issue_pkce_verifier, pkce_s256_challenge
from src.security.session_tokens import issue_session_token, session_expiry

router = APIRouter(prefix="/auth", tags=["authentication"])
_STATE_COOKIE = "asc_oauth_state"
_VERIFIER_COOKIE = "asc_oauth_verifier"
_SESSION_COOKIE = "asc_session"
_COMPANY_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"


def _provider_config(provider: str) -> tuple[str, str, str, str]:
    if provider == "google":
        return (
            settings.google_oauth_client_id,
            settings.google_oauth_client_secret,
            "https://accounts.google.com/o/oauth2/v2/auth",
            "https://oauth2.googleapis.com/token",
        )
    if provider == "github":
        return (
            settings.github_oauth_client_id,
            settings.github_oauth_client_secret,
            "https://github.com/login/oauth/authorize",
            "https://github.com/login/oauth/access_token",
        )
    raise HTTPException(status_code=404, detail="OAuth provider not supported")


def _callback_url(provider: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/auth/{provider}/callback"


def _set_short_cookie(response: Response, name: str, value: str) -> None:
    response.set_cookie(
        name,
        value,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/auth",
    )


@router.get("/{provider}/start")
async def oauth_start(provider: str) -> RedirectResponse:
    client_id, _, authorize_url, _ = _provider_config(provider)
    if not client_id:
        raise HTTPException(status_code=503, detail=f"{provider.title()} OAuth is not configured")
    state = issue_oauth_state()
    verifier = issue_pkce_verifier()
    params = {
        "client_id": client_id,
        "redirect_uri": _callback_url(provider),
        "response_type": "code",
        "state": state,
        "code_challenge": pkce_s256_challenge(verifier),
        "code_challenge_method": "S256",
    }
    if provider == "google":
        params.update({"scope": "openid email profile", "access_type": "online"})
    else:
        params["scope"] = "read:user user:email"
    response = RedirectResponse(
        str(httpx.URL(authorize_url).copy_merge_params(params)), status_code=302
    )
    _set_short_cookie(response, _STATE_COOKIE, state)
    _set_short_cookie(response, _VERIFIER_COOKIE, verifier)
    return response


async def _provider_profile(
    provider: str, code: str, verifier: str, client_id: str, client_secret: str
) -> tuple[str, str, str, str | None]:
    _, _, _, token_url = _provider_config(provider)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        token_response = await client.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": _callback_url(provider),
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
            headers={"Accept": "application/json"},
        )
        if token_response.status_code != 200:
            raise HTTPException(status_code=401, detail="OAuth token exchange failed")
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise HTTPException(status_code=401, detail="OAuth provider returned no access token")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        if provider == "google":
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo", headers=headers
            )
            if profile_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Could not verify Google identity")
            profile = profile_response.json()
            if profile.get("email_verified") is not True:
                raise HTTPException(status_code=403, detail="Google email must be verified")
            subject, email = profile.get("sub"), profile.get("email")
            name, avatar = profile.get("name") or "", profile.get("picture")
        else:
            profile_response = await client.get("https://api.github.com/user", headers=headers)
            if profile_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Could not verify GitHub identity")
            profile = profile_response.json()
            subject = str(profile.get("id") or "")
            email, name, avatar = None, profile.get("name") or profile.get("login") or "", profile.get("avatar_url")
            emails_response = await client.get("https://api.github.com/user/emails", headers=headers)
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary = next(
                    (item for item in emails if item.get("primary") and item.get("verified")),
                    None,
                )
                if primary:
                    email = primary.get("email")
        if not isinstance(subject, str) or not subject:
            raise HTTPException(status_code=401, detail="OAuth profile has no stable subject")
        if email is not None and not isinstance(email, str):
            email = None
        return subject, str(name or ""), str(avatar) if avatar else "", email


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    response: Response,
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    client_id, client_secret, _, _ = _provider_config(provider)
    expected_state = request.cookies.get(_STATE_COOKIE)
    verifier = request.cookies.get(_VERIFIER_COOKIE)
    if not expected_state or not state or not secrets_compare(state, expected_state) or not verifier:
        raise HTTPException(status_code=400, detail="OAuth state validation failed")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail=f"{provider.title()} OAuth is not configured")
    subject, display_name, avatar_url, email = await _provider_profile(
        provider, code, verifier, client_id, client_secret
    )
    identity_result = await db.execute(
        select(OAuthIdentityModel).where(
            OAuthIdentityModel.provider == provider,
            OAuthIdentityModel.provider_subject == subject,
        )
    )
    identity = identity_result.scalar_one_or_none()
    now = datetime.now(UTC)
    if identity:
        user_result = await db.execute(select(UserModel).where(UserModel.id == identity.user_id))
        user = user_result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=403, detail="Account is inactive")
    else:
        user = UserModel(
            id=str(uuid4()), email=email, display_name=display_name, avatar_url=avatar_url or None,
            is_active=True, created_at=now, updated_at=now,
        )
        db.add(user)
        await db.flush()
        db.add(OAuthIdentityModel(
            id=str(uuid4()), user_id=user.id, provider=provider,
            provider_subject=subject, provider_email=email, created_at=now,
        ))
        is_owner = bool(
            settings.owner_email and email and email.casefold() == settings.owner_email.casefold()
        )
        workspace_id = _COMPANY_WORKSPACE_ID if is_owner else str(uuid4())
        if is_owner:
            company_result = await db.execute(
                select(WorkspaceModel).where(WorkspaceModel.id == _COMPANY_WORKSPACE_ID)
            )
            if company_result.scalar_one_or_none() is None:
                raise HTTPException(status_code=503, detail="Company workspace migration is required")
        else:
            db.add(WorkspaceModel(
                id=workspace_id, name=f"{display_name or 'My'} Workspace", kind="personal",
                owner_user_id=user.id, expires_at=None, created_at=now,
            ))
        db.add(WorkspaceMembershipModel(
            id=str(uuid4()), workspace_id=workspace_id, user_id=user.id,
            role="owner", created_at=now,
        ))
    raw_token, token_hash = issue_session_token()
    expires_at = session_expiry(now=now)
    db.add(AuthSessionModel(
        id=str(uuid4()), user_id=user.id, demo_workspace_id=None, token_hash=token_hash,
        expires_at=expires_at, revoked=False, created_at=now,
    ))
    await db.commit()
    redirect = RedirectResponse(url="/app", status_code=303)
    redirect.delete_cookie(_STATE_COOKIE, path="/auth")
    redirect.delete_cookie(_VERIFIER_COOKIE, path="/auth")
    redirect.set_cookie(
        _SESSION_COOKIE, raw_token, max_age=int((expires_at - now).total_seconds()),
        httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/",
    )
    return redirect


def secrets_compare(left: str, right: str) -> bool:
    """Constant-time comparison for OAuth state values."""
    import hmac

    return hmac.compare_digest(left, right)



@router.get("/me")
async def current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | None]:
    """Return the signed-in identity only when its server-side session is valid."""
    from src.security.session_tokens import hash_session_token

    raw_token = request.cookies.get(_SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Sign-in required")
    result = await db.execute(
        select(AuthSessionModel).where(
            AuthSessionModel.token_hash == hash_session_token(raw_token),
            AuthSessionModel.revoked.is_(False),
            AuthSessionModel.expires_at > datetime.now(UTC),
        )
    )
    session = result.scalar_one_or_none()
    if session is None or session.user_id is None:
        raise HTTPException(status_code=401, detail="Session is invalid or expired")
    user_result = await db.execute(select(UserModel).where(UserModel.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Revoke the current server-side session and clear the browser cookie."""
    from src.security.session_tokens import hash_session_token

    raw_token = request.cookies.get(_SESSION_COOKIE)
    if raw_token:
        result = await db.execute(
            select(AuthSessionModel).where(
                AuthSessionModel.token_hash == hash_session_token(raw_token),
                AuthSessionModel.revoked.is_(False),
            )
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.revoked = True
            await db.commit()
    response.delete_cookie(_SESSION_COOKIE, path="/")
    response.status_code = 204
    return response
