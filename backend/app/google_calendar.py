"""Google integration — OAuth2 login + Calendar API access.

"Sign in with Google" is the only authentication method: a single consent grants
both the user's identity and Calendar access. The redirect URI is kept at
``/integrations/google/callback`` so existing Google Cloud console config keeps
working. Credentials are stored per-user in the ``google_credentials`` table and
reused by the calendar tools.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from . import repo
from .config import settings

logger = logging.getLogger("nova-agent")

# Google often returns scopes in a different order / adds `openid`; relax so
# oauthlib does not raise "Scope has changed".
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
]

_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def is_configured() -> bool:
    """Whether the server has Google OAuth client credentials set."""
    return bool(settings.google_client_id and settings.google_client_secret)


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def _flow() -> Flow:
    # PKCE is disabled: login URL and callback are handled by separate requests
    # with separate Flow instances, so a per-request code_verifier cannot be
    # shared. A confidential web client (with a client secret) does not need it.
    return Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=settings.google_redirect_uri,
        autogenerate_code_verifier=False,
    )


# ── Login (OAuth) ─────────────────────────────────────────────────────────────

def build_login_url() -> str:
    """The Google consent URL — grants identity + Calendar in one step."""
    auth_url, _ = _flow().authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


async def complete_login(session, code: str):
    """Exchange the OAuth code: fetch the Google profile, upsert the user, and
    store their credentials. Returns the User."""
    flow = _flow()
    await asyncio.to_thread(flow.fetch_token, code=code)
    creds = flow.credentials

    def _userinfo() -> dict:
        return AuthorizedSession(creds).get(_USERINFO_URL, timeout=10).json()

    info = await asyncio.to_thread(_userinfo)

    user = await repo.get_or_create_google_user(
        session,
        email=info["email"],
        name=info.get("name", ""),
        google_sub=info["id"],
        avatar_url=info.get("picture"),
    )
    await _store_credentials(session, user.id, creds)
    logger.info("[Google] Login + Calendar connected for %s", info["email"])
    return user


# ── Credentials storage ───────────────────────────────────────────────────────

async def _store_credentials(session, user_id: str, creds: Credentials) -> None:
    await repo.upsert_google_credential(
        session, user_id,
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        scopes=" ".join(creds.scopes or SCOPES),
        expiry=creds.expiry,
    )


async def is_connected(session, user_id: str) -> bool:
    return (await repo.get_google_credential(session, user_id)) is not None


async def _load_credentials(session, user_id: str) -> Credentials | None:
    row = await repo.get_google_credential(session, user_id)
    if not row:
        return None
    creds = Credentials(
        token=row.token,
        refresh_token=row.refresh_token,
        token_uri=row.token_uri,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=row.scopes.split() if row.scopes else SCOPES,
    )
    if creds.expired and creds.refresh_token:
        await asyncio.to_thread(creds.refresh, Request())
        await repo.upsert_google_credential(
            session, user_id, token=creds.token, expiry=creds.expiry,
        )
    return creds


# ── Calendar API ──────────────────────────────────────────────────────────────

async def list_events(
    session, user_id: str, time_min: datetime | None = None,
    time_max: datetime | None = None, max_results: int = 10,
) -> list[dict] | None:
    """Return upcoming events, or ``None`` if the user has no stored credentials."""
    creds = await _load_credentials(session, user_id)
    if not creds:
        return None

    def _call() -> list[dict]:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        params = {
            "calendarId": "primary",
            "timeMin": (time_min or datetime.now(timezone.utc)).isoformat(),
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_max:
            params["timeMax"] = time_max.isoformat()
        return service.events().list(**params).execute().get("items", [])

    return await asyncio.to_thread(_call)


def _aware(dt: datetime) -> datetime:
    """Attach the server's local timezone if the datetime is naive — the Google
    Calendar API rejects dateTime values without a timezone offset."""
    return dt if dt.tzinfo else dt.astimezone()


async def create_event(
    session, user_id: str, summary: str, start: datetime, end: datetime,
    description: str = "",
) -> dict | None:
    """Create an event, or return ``None`` if the user has no stored credentials."""
    creds = await _load_credentials(session, user_id)
    if not creds:
        return None

    def _call() -> dict:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": _aware(start).isoformat()},
            "end": {"dateTime": _aware(end).isoformat()},
        }
        return service.events().insert(calendarId="primary", body=body).execute()

    return await asyncio.to_thread(_call)
