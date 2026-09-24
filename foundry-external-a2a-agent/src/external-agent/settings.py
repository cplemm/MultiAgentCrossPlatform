from dataclasses import dataclass
import os


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    api_client_id: str
    api_client_secret: str
    api_audience: str
    required_scope: str
    public_base_url: str
    port: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            tenant_id=_required("AZURE_TENANT_ID"),
            api_client_id=_required("API_CLIENT_ID"),
            api_client_secret=_required("API_CLIENT_SECRET"),
            api_audience=os.getenv(
                "API_AUDIENCE",
                f"api://{_required('API_CLIENT_ID')}",
            ).strip(),
            required_scope=os.getenv(
                "API_REQUIRED_SCOPE",
                "access_as_user",
            ).strip(),
            public_base_url=_required("PUBLIC_BASE_URL").rstrip("/"),
            port=int(os.getenv("PORT", "8000")),
        )

