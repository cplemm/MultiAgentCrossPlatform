import logging
import time

import jwt
from mcp.server.auth.provider import AccessToken


logger = logging.getLogger(__name__)


class EntraTokenVerifier:
    def __init__(
        self,
        tenant_id: str,
        audience: str,
        required_scope: str,
    ) -> None:
        self._tenant_id = tenant_id
        self._issuers = [
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            f"https://sts.windows.net/{tenant_id}/",
        ]
        self._audience = audience
        self._audiences = [audience]
        if audience.startswith("api://"):
            self._audiences.append(audience.removeprefix("api://"))
        self._required_scope = required_scope
        self._jwks = jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}"
            "/discovery/v2.0/keys"
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audiences,
                issuer=self._issuers,
                options={"require": ["aud", "exp", "iat", "iss", "sub"]},
            )
        except jwt.PyJWKClientError as error:
            logger.warning("Unable to resolve an Entra signing key: %s", error)
            return None
        except jwt.PyJWTError:
            return None

        if claims.get("tid") != self._tenant_id:
            return None

        scopes = str(claims.get("scp", "")).split()
        if self._required_scope and self._required_scope not in scopes:
            return None

        expires_at = int(claims["exp"])
        if expires_at <= int(time.time()):
            return None

        client_id = str(
            claims.get("azp") or claims.get("appid") or "unknown-client"
        )
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            resource=self._audience,
        )
