from types import SimpleNamespace
import time

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from auth import EntraTokenVerifier, TokenValidationError


TENANT = "11111111-1111-1111-1111-111111111111"
CLIENT = "22222222-2222-2222-2222-222222222222"


class StaticJwks:
    def __init__(self, key) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, _token: str):
        return SimpleNamespace(key=self._key)


def make_token(
    private_key,
    *,
    audience: str = CLIENT,
    scopes: str = "access_as_user",
    tenant: str = TENANT,
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "aud": audience,
            "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
            "iat": now,
            "exp": now + 300,
            "sub": "subject",
            "oid": "object-id",
            "tid": tenant,
            "scp": scopes,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def verifier(public_key) -> EntraTokenVerifier:
    result = EntraTokenVerifier(
        tenant_id=TENANT,
        audience=f"api://{CLIENT}",
        required_scope="access_as_user",
    )
    result._jwks = StaticJwks(public_key)
    return result


@pytest.mark.asyncio
async def test_accepts_delegated_token() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    claims = await verifier(private_key.public_key()).verify(
        make_token(private_key)
    )
    assert claims["oid"] == "object-id"


@pytest.mark.asyncio
async def test_rejects_wrong_audience() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    with pytest.raises(TokenValidationError):
        await verifier(private_key.public_key()).verify(
            make_token(private_key, audience="wrong")
        )


@pytest.mark.asyncio
async def test_rejects_missing_scope() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    with pytest.raises(TokenValidationError, match="scope"):
        await verifier(private_key.public_key()).verify(
            make_token(private_key, scopes="other_scope")
        )

