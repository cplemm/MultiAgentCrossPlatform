import asyncio
from collections.abc import Sequence
import threading

import msal


class OboExchangeError(RuntimeError):
    pass


class OboTokenExchanger:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._application: msal.ConfidentialClientApplication | None = None
        self._initialization_lock = threading.Lock()

    def _get_application(self) -> msal.ConfidentialClientApplication:
        if self._application is not None:
            return self._application
        with self._initialization_lock:
            if self._application is None:
                self._application = msal.ConfidentialClientApplication(
                    client_id=self._client_id,
                    authority=(
                        f"https://login.microsoftonline.com/{self._tenant_id}"
                    ),
                    client_credential=self._client_secret,
                )
        return self._application

    def _acquire(
        self,
        user_assertion: str,
        scopes: Sequence[str],
    ) -> dict:
        return self._get_application().acquire_token_on_behalf_of(
            user_assertion=user_assertion,
            scopes=list(scopes),
        )

    async def exchange(
        self,
        user_assertion: str,
        scopes: Sequence[str],
    ) -> str:
        result = await asyncio.to_thread(
            self._acquire,
            user_assertion,
            scopes,
        )
        token = result.get("access_token")
        if token:
            return str(token)

        code = result.get("error", "unknown_error")
        description = result.get(
            "error_description", "Microsoft Entra ID returned no access token"
        )
        raise OboExchangeError(f"OBO exchange failed: {code}: {description}")
