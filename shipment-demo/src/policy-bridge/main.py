from datetime import datetime, timezone
import json
import logging
from time import perf_counter

from dotenv import load_dotenv
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import Context, FastMCP
from pydantic import AnyHttpUrl

from auth import EntraTokenVerifier
from copilot import PolicyAnalyzer, PolicyRequest
from obo import OboTokenExchanger
from settings import Settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("shipment-policy-bridge")
load_dotenv(override=False)
settings = Settings.from_env()
verifier = EntraTokenVerifier(
    tenant_id=settings.tenant_id,
    audience=settings.bridge_audience,
    required_scope=settings.bridge_scope,
)
analyzer = PolicyAnalyzer(
    connection=settings.copilot_connection(),
    exchanger=OboTokenExchanger(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    ),
)
mcp = FastMCP(
    name="purchasing-policy-specialist",
    instructions=(
        "Evaluates delayed-shipment recovery options against the configured "
        "Copilot Studio purchasing policy using delegated user identity."
    ),
    host=settings.host,
    port=settings.port,
    streamable_http_path="/mcp",
    stateless_http=True,
    token_verifier=verifier,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(
            f"https://login.microsoftonline.com/{settings.tenant_id}/v2.0"
        ),
        resource_server_url=AnyHttpUrl(settings.public_url),
        required_scopes=[settings.bridge_scope],
    ),
)


@mcp.tool(
    name="evaluate_recovery_policy",
    description=(
        "Evaluate proposed recovery options for a delayed shipment against "
        "the configured purchasing policy."
    ),
)
async def evaluate_recovery_policy(
    shipment_id: str,
    part_number: str,
    required_units: int,
    launch_date: str,
    proposed_options_json: str,
    ctx: Context,
) -> dict:
    access_token = get_access_token()
    if access_token is None:
        raise PermissionError("A delegated user token is required")
    started = perf_counter()
    start_time = datetime.now(timezone.utc)
    result = await analyzer.evaluate(
        access_token.token,
        PolicyRequest(
            shipment_id=shipment_id.strip().upper(),
            part_number=part_number.strip().upper(),
            required_units=required_units,
            launch_date=launch_date.strip(),
            proposed_options_json=proposed_options_json,
        ),
    )
    logger.info(
        json.dumps(
            {
                "event": "policy_evaluation_completed",
                "request_id": str(ctx.request_id),
                "shipment_id": shipment_id.strip().upper(),
                "cps_conversation_id": result.conversation_id,
                "cps_message_activity_count": result.message_activity_count,
                "start_time": start_time.isoformat(),
                "duration_ms": round((perf_counter() - started) * 1000),
            },
            separators=(",", ":"),
        )
    )
    return {
        "policy": result.policy,
        "delegation": "Copilot Studio via Microsoft Entra OBO",
        "cps_conversation_id": result.conversation_id,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
