import asyncio
import logging
import time

import jwt


logger = logging.getLogger(__name__)


class TokenValidationError(ValueError):
    pass


class EntraTokenVerifier:
    def __init__(
        self,
        tenant_id: str,
        audience: str,
        required_scope: str,
    ) -> None:
        self._tenant_id = tenant_id
        self._issuer = (
            f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        )
        self._audiences = [audience]
        if audience.startswith("api://"):
            self._audiences.append(audience.removeprefix("api://"))
        self._required_scope = required_scope
        self._jwks = jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}"
            "/discovery/v2.0/keys"
        )

    async def verify(self, token: str) -> dict:
        try:
            signing_key = await asyncio.to_thread(
                self._jwks.get_signing_key_from_jwt,
                token,
            )
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audiences,
                issuer=self._issuer,
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "sub",
                        "tid",
                    ]
                },
            )
        except jwt.PyJWKClientError as error:
            logger.warning("Unable to resolve an Entra signing key: %s", error)
            raise TokenValidationError("Token signing key is unavailable") from error
        except jwt.PyJWTError as error:
            raise TokenValidationError("Token validation failed") from error

        if claims.get("tid") != self._tenant_id:
            raise TokenValidationError("Token tenant is not allowed")

        scopes = str(claims.get("scp", "")).split()
        if self._required_scope not in scopes:
            raise TokenValidationError("Required delegated scope is missing")

        if int(claims["exp"]) <= int(time.time()):
            raise TokenValidationError("Token has expired")

        return claims


def extract_bearer_token(value: str | None) -> str:
    if not value:
        raise TokenValidationError("Authorization header is missing")
    scheme, separator, token = value.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise TokenValidationError("Authorization header must use Bearer")
    return token.strip()

