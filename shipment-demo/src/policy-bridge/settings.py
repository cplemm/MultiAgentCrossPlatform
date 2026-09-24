from dataclasses import dataclass
import os

from microsoft_agents.copilotstudio.client import (
    ConnectionSettings,
    PowerPlatformCloud,
)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    client_secret: str
    bridge_audience: str
    bridge_scope: str
    public_url: str
    cps_environment_id: str
    cps_schema_name: str
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            tenant_id=_required("AZURE_TENANT_ID"),
            client_id=_required("POLICY_BRIDGE_CLIENT_ID"),
            client_secret=_required("POLICY_BRIDGE_CLIENT_SECRET"),
            bridge_audience=_required("POLICY_BRIDGE_AUDIENCE"),
            bridge_scope=os.getenv(
                "POLICY_BRIDGE_REQUIRED_SCOPE",
                "access_as_user",
            ).strip(),
            public_url=_required("POLICY_BRIDGE_URL").rstrip("/"),
            cps_environment_id=_required("COPILOT_STUDIO_ENVIRONMENT_ID"),
            cps_schema_name=_required("COPILOT_STUDIO_SCHEMA_NAME"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
        )

    def copilot_connection(self) -> ConnectionSettings:
        return ConnectionSettings(
            environment_id=self.cps_environment_id,
            agent_identifier=self.cps_schema_name,
            cloud=PowerPlatformCloud.PROD,
            copilot_agent_type=None,
            custom_power_platform_cloud=None,
        )
