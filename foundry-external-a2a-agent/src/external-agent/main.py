import logging

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from agent_executor import GraphProfileAgentExecutor
from auth import (
    EntraTokenVerifier,
    TokenValidationError,
    extract_bearer_token,
)
from obo import GraphOboClient
from settings import Settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("external-a2a-agent")
settings = Settings.from_env()
verifier = EntraTokenVerifier(
    tenant_id=settings.tenant_id,
    audience=settings.api_audience,
    required_scope=settings.required_scope,
)


class DelegatedAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path == "/":
            try:
                token = extract_bearer_token(
                    request.headers.get("authorization")
                )
                claims = await verifier.verify(token)
                logger.info(
                    "Accepted delegated A2A request oid=%s",
                    claims.get("oid", "unknown"),
                )
            except TokenValidationError as error:
                return JSONResponse(
                    {"error": "unauthorized", "message": str(error)},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)


async def health(_request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


skill = AgentSkill(
    id="delegated-graph-profile",
    name="Delegated Microsoft Graph profile",
    description=(
        "Retrieves the signed-in user's Microsoft Graph profile using "
        "OAuth 2.0 on-behalf-of delegation."
    ),
    tags=["identity", "microsoft-graph", "obo"],
    examples=["Who am I?", "Show my delegated identity"],
    input_modes=["text/plain"],
    output_modes=["application/json", "text/plain"],
)
card = AgentCard(
    name="External Graph Profile Agent",
    description=(
        "An external A2A agent on Azure Container Apps that demonstrates "
        "delegated OAuth and OBO to Microsoft Graph."
    ),
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["application/json", "text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            protocol_version="1.0",
            url=settings.public_base_url,
        )
    ],
    skills=[skill],
)
handler = DefaultRequestHandler(
    agent_executor=GraphProfileAgentExecutor(
        verifier=verifier,
        graph_obo=GraphOboClient(
            tenant_id=settings.tenant_id,
            client_id=settings.api_client_id,
            client_secret=settings.api_client_secret,
        ),
    ),
    task_store=InMemoryTaskStore(),
    agent_card=card,
)
routes = [
    Route("/healthz", health, methods=["GET"]),
    *create_agent_card_routes(card),
    *create_jsonrpc_routes(handler, rpc_url="/"),
]
app = Starlette(routes=routes)
app.add_middleware(DelegatedAuthMiddleware)

