from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import PyJWK
from jwt.exceptions import InvalidTokenError as PyJwtInvalidTokenError
from jwt.exceptions import PyJWTError


class InvalidAccessToken(ValueError):
    """The caller supplied credentials that cannot be trusted."""


class IdentityProviderUnavailable(RuntimeError):
    """The configured identity provider cannot currently supply trusted keys."""


@dataclass(frozen=True)
class JwtIdentity:
    issuer: str
    subject: str


class JwtVerifier:
    """Verify OIDC access tokens using an asynchronously refreshed JWKS cache."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        required_scope: str,
        timeout_seconds: float,
        cache_ttl_seconds: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not all(value.strip() for value in (issuer, audience, jwks_url, required_scope)):
            raise ValueError("OIDC verifier settings must not be blank")
        if timeout_seconds <= 0 or cache_ttl_seconds <= 0:
            raise ValueError("OIDC timeout and cache TTL must be positive")

        self._issuer = issuer
        self._audience = audience
        self._jwks_url = jwks_url
        self._required_scope = required_scope
        self._cache_ttl_seconds = cache_ttl_seconds
        self._keys: dict[str, PyJWK] = {}
        self._cache_expires_at = 0.0
        self._refresh_lock = asyncio.Lock()
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def verify(self, token: str) -> JwtIdentity:
        try:
            header = jwt.get_unverified_header(token)
        except PyJwtInvalidTokenError as error:
            raise InvalidAccessToken("access token is malformed") from error

        if header.get("alg") != "RS256":
            raise InvalidAccessToken("access token algorithm is not allowed")
        key_id = header.get("kid")
        if not isinstance(key_id, str) or not key_id:
            raise InvalidAccessToken("access token key identifier is missing")

        signing_key = await self._signing_key(key_id)
        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except PyJwtInvalidTokenError as error:
            raise InvalidAccessToken("access token validation failed") from error

        subject = claims.get("sub")
        issuer = claims.get("iss")
        if not isinstance(subject, str) or not subject.strip() or issuer != self._issuer:
            raise InvalidAccessToken("access token identity is invalid")
        if self._required_scope not in self._token_scopes(claims):
            raise InvalidAccessToken("access token scope is insufficient")
        return JwtIdentity(issuer=issuer, subject=subject)

    async def _signing_key(self, key_id: str) -> PyJWK:
        now = time.monotonic()
        if now < self._cache_expires_at:
            key = self._keys.get(key_id)
            if key is None:
                raise InvalidAccessToken("access token signing key is unknown")
            return key

        async with self._refresh_lock:
            now = time.monotonic()
            if now >= self._cache_expires_at:
                await self._refresh_keys(now)
            key = self._keys.get(key_id)
        if key is None:
            raise InvalidAccessToken("access token signing key is unknown")
        return key

    async def _refresh_keys(self, now: float) -> None:
        try:
            response = await self._client.get(self._jwks_url)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise IdentityProviderUnavailable("identity provider keys are unavailable") from error

        raw_keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(raw_keys, list):
            raise IdentityProviderUnavailable("identity provider returned an invalid JWKS")

        parsed: dict[str, PyJWK] = {}
        for raw_key in raw_keys:
            if not isinstance(raw_key, dict):
                continue
            key_id = raw_key.get("kid")
            if (
                not isinstance(key_id, str)
                or not key_id
                or raw_key.get("kty") != "RSA"
                or raw_key.get("alg") not in (None, "RS256")
                or raw_key.get("use") not in (None, "sig")
            ):
                continue
            try:
                parsed[key_id] = PyJWK.from_dict(raw_key, algorithm="RS256")
            except (KeyError, PyJWTError, ValueError, TypeError):
                continue
        if not parsed:
            raise IdentityProviderUnavailable("identity provider returned no usable signing keys")

        self._keys = parsed
        self._cache_expires_at = now + self._cache_ttl_seconds

    @staticmethod
    def _token_scopes(claims: dict[str, Any]) -> set[str]:
        scope = claims.get("scope")
        if isinstance(scope, str):
            return set(scope.split())
        scopes = claims.get("scp")
        if isinstance(scopes, list) and all(isinstance(item, str) for item in scopes):
            return set(scopes)
        return set()
