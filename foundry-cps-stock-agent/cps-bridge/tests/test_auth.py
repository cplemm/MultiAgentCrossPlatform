from types import SimpleNamespace
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
import pytest

from auth import EntraTokenVerifier


TENANT_ID = "11111111-1111-1111-1111-111111111111"
CLIENT_ID = "22222222-2222-2222-2222-222222222222"


class StaticJwks:
    def __init__(self, key) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, _token: str):
        return SimpleNamespace(key=self._key)


def _token(private_key, issuer: str, audience: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "aud": audience,
            "iss": issuer,
            "iat": now,
            "exp": now + 300,
            "sub": "user-id",
            "tid": TENANT_ID,
            "scp": "access_as_user",
            "azp": "calling-client",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


async def _verify(issuer: str, audience: str):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    verifier = EntraTokenVerifier(
        tenant_id=TENANT_ID,
        audience=f"api://{CLIENT_ID}",
        required_scope="access_as_user",
    )
    verifier._jwks = StaticJwks(private_key.public_key())
    return await verifier.verify_token(
        _token(private_key, issuer, audience)
    )


@pytest.mark.asyncio
async def test_accepts_v2_issuer_and_app_id_uri_audience() -> None:
    result = await _verify(
        f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        f"api://{CLIENT_ID}",
    )
    assert result is not None


@pytest.mark.asyncio
async def test_accepts_v1_issuer_and_bare_client_id_audience() -> None:
    result = await _verify(
        f"https://sts.windows.net/{TENANT_ID}/",
        CLIENT_ID,
    )
    assert result is not None
