"""OAuth 2.1 (auth-code + PKCE, then refresh) against Upwork's MCP auth server.

Two entry points:
  * build_authorize_url() / exchange_code()  -> used once by bootstrap.py (browser login)
  * get_access_token(refresh_token)          -> used every run, unattended

Upwork advertises client_id_metadata_document_supported=true, so CLIENT_ID is a
URL (client-metadata.json) rather than a portal-issued id. token_endpoint auth
method is "none" (public client), so PKCE + the resource indicator carry the flow.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time

import httpx

import config


def make_pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(code_challenge: str, state: str) -> str:
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "resource": config.MCP_RESOURCE,
    }
    if config.__dict__.get("SCOPE"):
        params["scope"] = config.SCOPE
    return f"{config.AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


def exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange the auth code for tokens. Returns the raw token response dict."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
        "client_id": config.CLIENT_ID,
        "code_verifier": code_verifier,
        "resource": config.MCP_RESOURCE,
    }
    r = httpx.post(config.TOKEN_ENDPOINT, data=data, timeout=30)
    r.raise_for_status()
    return r.json()


def refresh(refresh_token: str) -> dict:
    """Trade a refresh token for a fresh access token (and maybe a rotated refresh token)."""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": config.CLIENT_ID,
        "resource": config.MCP_RESOURCE,
    }
    r = httpx.post(config.TOKEN_ENDPOINT, data=data, timeout=30)
    r.raise_for_status()
    return r.json()


def get_access_token(refresh_token: str) -> tuple[str, str | None]:
    """Unattended path: returns (access_token, maybe_new_refresh_token).

    Logs token lifetimes so we can empirically answer the longevity question.
    """
    tok = refresh(refresh_token)
    expires_in = tok.get("expires_in")
    print(f"[auth] got access token, expires_in={expires_in}s at {time.ctime()}")
    return tok["access_token"], tok.get("refresh_token")
