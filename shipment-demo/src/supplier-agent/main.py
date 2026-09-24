import json
import os
from pathlib import Path

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    TaskState,
)
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


load_dotenv(override=False)
base_url = os.environ["PUBLIC_BASE_URL"].rstrip("/")
inventory_path = Path(os.getenv("INVENTORY_PATH", "data/inventory.json"))


class SupplierExecutor(AgentExecutor):
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task or new_task_from_user_message(
            context.message
        )
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        request_text = (get_message_text(context.message) or "").upper()
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        part_number = next(
            (
                offer["part_number"]
                for offer in inventory["offers"]
                if offer["part_number"] in request_text
            ),
            "BAT-48V-750",
        )
        offers = [
            offer
            for offer in inventory["offers"]
            if offer["part_number"] == part_number
        ]
        payload = {
            "part_number": part_number,
            "offers": offers,
            "source": "Synthetic supplier inventory",
        }
        await updater.add_artifact(
            parts=[
                new_text_part(
                    text=json.dumps(payload, ensure_ascii=True),
                    media_type="application/json",
                )
            ]
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message(
                f"Returned {len(offers)} synthetic supplier offers."
            ),
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise NotImplementedError("Cancellation is not supported")


async def health(_request):
    return PlainTextResponse("ok")


card = AgentCard(
    name="Shipment Supplier Specialist",
    description=(
        "Queries synthetic supplier inventory for delayed-shipment recovery."
    ),
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["application/json", "text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            protocol_version="1.0",
            url=base_url,
        )
    ],
    skills=[
        AgentSkill(
            id="supplier-availability",
            name="Supplier availability",
            description=(
                "Returns alternate supplier availability, ETA, cost, expedite "
                "fee, and quality status for a requested part."
            ),
            tags=["shipment", "inventory", "supplier"],
            examples=["Find alternate supply for BAT-48V-750"],
            input_modes=["text/plain"],
            output_modes=["application/json", "text/plain"],
        )
    ],
)
handler = DefaultRequestHandler(
    agent_executor=SupplierExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=card,
)
app = Starlette(
    routes=[
        Route("/healthz", health, methods=["GET"]),
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ]
)
