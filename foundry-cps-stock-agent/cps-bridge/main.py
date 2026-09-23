from datetime import datetime, timezone
import json
import logging
from time import perf_counter

import aiohttp
from dotenv import load_dotenv
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import Context, FastMCP
from pydantic import AnyHttpUrl, ValidationError

from auth import EntraTokenVerifier
from copilot import (
    CopilotStudioAnalyzer,
    CopilotStudioNoMessageError,
    StockEvidence,
    validate_evidence,
)
from obo import OboExchangeError, OboTokenExchanger
from settings import Settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("cps-stock-bridge")

load_dotenv(override=False)
settings = Settings.from_env()
verifier = EntraTokenVerifier(
    tenant_id=settings.tenant_id,
    audience=settings.bridge_audience,
    required_scope=settings.bridge_scope,
)
analyzer = CopilotStudioAnalyzer(
    connection=settings.copilot_connection(),
    exchanger=OboTokenExchanger(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    ),
)
mcp = FastMCP(
    name="copilot-studio-stock-analysis",
    instructions=(
        "Delegates current stock-market research to a Copilot Studio agent "
        "using the signed-in user's delegated identity."
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _failure_category(error: Exception) -> str:
    if isinstance(error, PermissionError):
        return "inbound_authentication"
    if isinstance(error, ValueError) and not isinstance(error, ValidationError):
        return "input_validation"
    if isinstance(error, OboExchangeError):
        return "obo_exchange"
    if isinstance(error, aiohttp.ClientResponseError):
        return "cps_http_response"
    if isinstance(error, aiohttp.ClientError):
        return "cps_transport"
    if isinstance(error, ValidationError):
        return "cps_response_schema"
    if isinstance(error, CopilotStudioNoMessageError):
        return "cps_empty_response"
    return "unexpected"


def _log_lifecycle(level: int, **fields) -> None:
    logger.log(
        level,
        json.dumps(fields, ensure_ascii=True, separators=(",", ":")),
    )


@mcp.tool(
    name="analyze_stock",
    description=(
        "Ask the configured Copilot Studio financial analyst to research and "
        "summarize a stock after the caller has obtained a current price."
    ),
)
async def analyze_stock(
    symbol: str,
    observed_price: str,
    currency: str,
    market_state: str,
    as_of: str,
    source_url: str,
    ctx: Context,
) -> dict[str, str]:
    request_id = str(ctx.request_id)
    log_symbol = symbol.strip().upper()[:20]
    start_time = _utc_now()
    started = perf_counter()
    _log_lifecycle(
        logging.INFO,
        event="stock_analysis_started",
        request_id=request_id,
        cps_conversation_id=None,
        symbol=log_symbol,
        start_time=start_time.isoformat(),
        end_time=None,
        duration_ms=0,
        cps_message_activity_count=0,
        outcome="in_progress",
        category="started",
    )

    try:
        access_token = get_access_token()
        if access_token is None:
            raise PermissionError("A delegated user token is required")

        evidence = validate_evidence(StockEvidence(
            symbol=symbol.strip().upper(),
            observed_price=observed_price.strip(),
            currency=currency.strip().upper(),
            market_state=market_state.strip(),
            as_of=as_of.strip(),
            source_url=source_url.strip(),
        ))
        result = await analyzer.analyze(access_token.token, evidence)
        end_time = _utc_now()
        duration_ms = round((perf_counter() - started) * 1000)
        _log_lifecycle(
            logging.INFO,
            event="stock_analysis_completed",
            request_id=request_id,
            cps_conversation_id=result.conversation_id,
            symbol=evidence.symbol,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_ms=duration_ms,
            cps_message_activity_count=result.message_activity_count,
            outcome="success",
            category="completed",
        )
        return {
            "symbol": evidence.symbol,
            "analysis": result.analysis,
            "delegation": "Copilot Studio via Microsoft Entra OBO",
        }
    except Exception as error:
        end_time = _utc_now()
        duration_ms = round((perf_counter() - started) * 1000)
        _log_lifecycle(
            logging.ERROR,
            event="stock_analysis_failed",
            request_id=request_id,
            cps_conversation_id=getattr(
                error,
                "cps_conversation_id",
                None,
            ),
            symbol=log_symbol,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_ms=duration_ms,
            cps_message_activity_count=getattr(
                error,
                "cps_message_activity_count",
                0,
            ),
            outcome="failure",
            category=_failure_category(error),
            exception_type=type(error).__name__,
        )
        raise


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
