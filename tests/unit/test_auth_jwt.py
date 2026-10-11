from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from doclens_ai.api.dependencies import role_allows
from doclens_ai.models import WorkspaceRole
from doclens_ai.security import (
    IdentityProviderUnavailable,
    InvalidAccessToken,
    JwtVerifier,
)

ISSUER = "https://issuer.test/"
AUDIENCE = "doclens-api"
JWKS_URL = "https://issuer.test/.well-known/jwks.json"
KEY_ID = "test-key"
REQUIRED_SCOPE = "doclens:documents"


def _base64url(number: int) -> str:
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@pytest.fixture(scope="module")
def signing_material() -> tuple[rsa.RSAPrivateKey, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": KEY_ID,
        "use": "sig",
        "alg": "RS256",
        "n": _base64url(public_numbers.n),
        "e": _base64url(public_numbers.e),
    }
    return private_key, jwk


def _claims(**overrides: Any) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "subject-123",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "scope": REQUIRED_SCOPE,
    }
    claims.update(overrides)
    return claims


def _token(
    private_key: rsa.RSAPrivateKey | str,
    *,
    algorithm: str = "RS256",
    key_id: str = KEY_ID,
    claims: dict[str, Any] | None = None,
) -> str:
    return jwt.encode(
        claims or _claims(),
        private_key,
        algorithm=algorithm,
        headers={"kid": key_id},
    )


def _verifier(
    transport: httpx.BaseTransport,
    *,
    cache_ttl_seconds: int = 300,
) -> JwtVerifier:
    return JwtVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=JWKS_URL,
        required_scope=REQUIRED_SCOPE,
        timeout_seconds=1,
        cache_ttl_seconds=cache_ttl_seconds,
        client=httpx.AsyncClient(transport=transport),
    )


@pytest.mark.anyio
async def test_valid_rs256_token_is_verified_and_jwks_is_cached(
    signing_material: tuple[rsa.RSAPrivateKey, dict[str, Any]],
) -> None:
    private_key, jwk = signing_material
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        assert str(request.url) == JWKS_URL
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = _verifier(httpx.MockTransport(handler))
    token = _token(private_key)

    first = await verifier.verify(token)
    second = await verifier.verify(token)

    assert first == second
    assert first.issuer == ISSUER
    assert first.subject == "subject-123"
    assert requests == 1
    await verifier.aclose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "claim_changes",
    [
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"iss": "https://wrong-issuer.test/"},
        {"aud": "wrong-audience"},
        {"sub": ""},
        {"scope": "profile"},
    ],
    ids=["expired", "wrong-issuer", "wrong-audience", "missing-identity", "bad-scope"],
)
async def test_invalid_claims_are_rejected(
    signing_material: tuple[rsa.RSAPrivateKey, dict[str, Any]],
    claim_changes: dict[str, Any],
) -> None:
    private_key, jwk = signing_material
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"keys": [jwk]}))
    verifier = _verifier(transport)

    with pytest.raises(InvalidAccessToken):
        await verifier.verify(_token(private_key, claims=_claims(**claim_changes)))
    await verifier.aclose()


@pytest.mark.anyio
async def test_bad_signature_is_rejected(
    signing_material: tuple[rsa.RSAPrivateKey, dict[str, Any]],
) -> None:
    _, jwk = signing_material
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = _verifier(
        httpx.MockTransport(lambda request: httpx.Response(200, json={"keys": [jwk]}))
    )

    with pytest.raises(InvalidAccessToken):
        await verifier.verify(_token(wrong_key))
    await verifier.aclose()


@pytest.mark.anyio
async def test_malformed_token_and_missing_subject_are_rejected(
    signing_material: tuple[rsa.RSAPrivateKey, dict[str, Any]],
) -> None:
    private_key, jwk = signing_material
    verifier = _verifier(
        httpx.MockTransport(lambda request: httpx.Response(200, json={"keys": [jwk]}))
    )

    with pytest.raises(InvalidAccessToken, match="malformed"):
        await verifier.verify("not-a-jwt")
    claims = _claims()
    del claims["sub"]
    with pytest.raises(InvalidAccessToken):
        await verifier.verify(_token(private_key, claims=claims))
    await verifier.aclose()


@pytest.mark.anyio
async def test_non_rs256_algorithm_is_rejected_before_jwks_fetch() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(500)

    verifier = _verifier(httpx.MockTransport(handler))
    token = _token("test-secret-at-least-32-bytes-long", algorithm="HS256")

    with pytest.raises(InvalidAccessToken, match="algorithm"):
        await verifier.verify(token)
    assert requests == 0
    await verifier.aclose()


@pytest.mark.anyio
async def test_jwks_failure_is_temporary_provider_failure(
    signing_material: tuple[rsa.RSAPrivateKey, dict[str, Any]],
) -> None:
    private_key, _ = signing_material

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("issuer offline", request=request)

    verifier = _verifier(httpx.MockTransport(handler))

    with pytest.raises(IdentityProviderUnavailable):
        await verifier.verify(_token(private_key))
    await verifier.aclose()


@pytest.mark.parametrize(
    ("role", "write", "allowed"),
    [
        (WorkspaceRole.OWNER, True, True),
        (WorkspaceRole.EDITOR, True, True),
        (WorkspaceRole.VIEWER, True, False),
        (WorkspaceRole.OWNER, False, True),
        (WorkspaceRole.EDITOR, False, True),
        (WorkspaceRole.VIEWER, False, True),
        ("unknown", False, False),
    ],
)
def test_workspace_role_matrix(role: str, write: bool, allowed: bool) -> None:
    assert role_allows(role, write=write) is allowed
