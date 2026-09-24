from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from agent_framework import (
    Agent,
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentResponse,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.foundry import FoundryChatClient

from domain import (
    as_json,
    load_demo_data,
    parse_offers,
    parse_policy,
    resolve_shipment,
)
from planner import build_recovery_options, recommend_option
from specialists import (
    MockPolicySpecialist,
    SupplierSpecialist,
    build_specialist_workflow,
)


def _messages_text(messages: list[Message]) -> str:
    return "\n".join(message.text for message in messages if message.text)


def _json_messages(messages: list[Message]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for message in messages:
        if not message.text:
            continue
        start = message.text.find("{")
        end = message.text.rfind("}")
        if start < 0 or end < start:
            continue
        try:
            payloads.append(json.loads(message.text[start : end + 1]))
        except json.JSONDecodeError:
            continue
    return payloads


def _extract_policy(policy_entry: dict[str, Any]) -> dict[str, Any]:
    required = {
        "alternate_supplier_allowed",
        "split_shipment_allowed",
        "minimum_units_by_launch",
        "max_incremental_cost",
        "max_expedite_fee",
    }
    candidates = [
        policy_entry,
        policy_entry.get("policy"),
        policy_entry.get("result"),
        policy_entry.get("structured_content"),
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        nested = candidate.get("policy")
        if isinstance(nested, dict) and required <= nested.keys():
            return nested
        if required <= candidate.keys():
            return candidate
    keys = ", ".join(sorted(policy_entry))
    raise RuntimeError(
        f"Policy specialist returned no structured policy (keys: {keys})"
    )


class ShipmentIntake(Executor):
    def __init__(self, data_path: str, id: str = "shipment_intake"):
        super().__init__(id=id)
        self._data_path = data_path

    async def _emit(
        self,
        messages: list[Message],
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        data = load_demo_data(self._data_path)
        shipment = resolve_shipment(_messages_text(messages), data)
        payload = {
            "request": "Analyze this delayed shipment and recommend recovery.",
            "shipment": json.loads(as_json(shipment)),
        }
        response = AgentResponse(
            messages=[Message("assistant", [as_json(payload)])]
        )
        await ctx.send_message(
            AgentExecutorResponse(
                self.id,
                response,
                full_conversation=messages + list(response.messages),
            )
        )

    @handler
    async def from_str(
        self,
        text: str,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        await self._emit([Message("user", [text])], ctx)

    @handler
    async def from_messages(
        self,
        messages: list[Message],
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        await self._emit(messages, ctx)

    @handler
    async def from_request(
        self,
        request: AgentExecutorRequest,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        await self._emit(list(request.messages), ctx)


class SpecialistFanOut(Executor):
    def __init__(self, workflow, id: str = "specialist_fan_out"):
        super().__init__(id=id)
        self._workflow = workflow

    @handler
    async def run(
        self,
        prior: AgentExecutorResponse,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        events = await self._workflow.run(prior.full_conversation)
        outputs = events.get_outputs()
        if not outputs:
            raise RuntimeError("Concurrent specialist workflow returned no output")
        output = outputs[0]
        if isinstance(output, AgentResponse):
            response = output
        elif isinstance(output, str):
            response = AgentResponse(
                messages=[Message("assistant", [output])]
            )
        else:
            response = AgentResponse(
                messages=[Message("assistant", [str(output)])]
            )
        await ctx.send_message(
            AgentExecutorResponse(
                self.id,
                response,
                full_conversation=(
                    list(prior.full_conversation) + list(response.messages)
                ),
            )
        )


class RecoveryPlanner(Executor):
    def __init__(self, data_path: str, id: str = "recovery_planner"):
        super().__init__(id=id)
        self._data_path = data_path

    @handler
    async def run(
        self,
        prior: AgentExecutorResponse,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        data = load_demo_data(self._data_path)
        messages = list(prior.full_conversation)
        payloads = _json_messages(messages)
        intake_data = next(
            (item for item in payloads if "shipment" in item),
            None,
        )
        specialist_data = next(
            (item for item in payloads if "specialists" in item),
            None,
        )
        if intake_data is None or specialist_data is None:
            raise RuntimeError("Workflow context is missing shipment or specialist data")
        shipment = resolve_shipment(
            str(intake_data["shipment"]["shipment_id"]),
            data,
        )
        specialists = specialist_data["specialists"]
        policy_entry = specialists["purchasing_policy_specialist"]
        supplier_entry = specialists["supplier_specialist"]

        policy = parse_policy(_extract_policy(policy_entry))
        supplier_payload = supplier_entry["supplier"]
        offers = parse_offers(supplier_payload)
        options = build_recovery_options(shipment, policy, offers)
        recommendation = recommend_option(options)
        payload = {
            "shipment": json.loads(as_json(shipment)),
            "policy": json.loads(as_json(policy)),
            "options": [json.loads(as_json(option)) for option in options],
            "recommended_option": json.loads(as_json(recommendation)),
        }
        response = AgentResponse(
            messages=[Message("assistant", [as_json(payload)])]
        )
        await ctx.send_message(
            AgentExecutorResponse(
                self.id,
                response,
                full_conversation=messages + list(response.messages),
            )
        )


def _build_remote_planner_payload(
    messages: list[Message],
) -> dict[str, Any]:
    payloads = _json_messages(messages)
    intake_data = next(
        (item for item in payloads if "shipment" in item),
        None,
    )
    specialist_data = next(
        (item for item in payloads if "specialists" in item),
        None,
    )
    if intake_data is None or specialist_data is None:
        raise RuntimeError("Workflow context is missing shipment or specialist data")
    specialists = specialist_data["specialists"]
    policy_entry = specialists["purchasing_policy_specialist"]
    supplier_entry = specialists["supplier_specialist"]
    return {
        "shipment": intake_data["shipment"],
        "policy": _extract_policy(policy_entry),
        "supplier": supplier_entry["supplier"],
    }


def _response_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    parts = [
        content["text"]
        for item in payload.get("output", [])
        if isinstance(item, dict)
        for content in item.get("content", [])
        if isinstance(content, dict)
        and content.get("type") == "output_text"
        and isinstance(content.get("text"), str)
    ]
    return "\n".join(parts)


class RemoteRecoveryPlanner(Executor):
    def __init__(
        self,
        endpoint: str,
        credential,
        id: str = "remote_recovery_planner",
    ):
        super().__init__(id=id)
        self._endpoint = endpoint
        self._credential = credential

    @handler
    async def run(
        self,
        prior: AgentExecutorResponse,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        messages = list(prior.full_conversation)
        payload = _build_remote_planner_payload(messages)
        request_text = (
            "Calculate and rank recovery options using this structured input. "
            "Return only structured JSON.\n"
            + json.dumps(payload, ensure_ascii=True, sort_keys=True)
        )
        token = await asyncio.to_thread(
            self._credential.get_token,
            "https://ai.azure.com/.default",
        )
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {token.token}"},
                json={"input": request_text, "store": False},
            )
            response.raise_for_status()
        output_text = _response_output_text(response.json())
        if not output_text:
            raise RuntimeError("Remote Recovery Planner returned no output")
        response = AgentResponse(
            messages=[Message("assistant", [output_text])]
        )
        await ctx.send_message(
            AgentExecutorResponse(
                self.id,
                response,
                full_conversation=messages + list(response.messages),
            )
        )


def build_workflow_agent(
    chat_client: FoundryChatClient,
    toolbox,
    credential,
):
    data_path = os.getenv("SHIPMENT_DATA_PATH", "data/shipments.json")
    mode = os.getenv("SHIPMENT_DEMO_MODE", "mock").lower()

    if mode == "connected":
        if toolbox is None:
            raise RuntimeError("Connected mode requires a Foundry toolbox")
        policy_specialist = Agent(
            client=chat_client,
            name="purchasing_policy_specialist",
            instructions=(
                "You are the Purchasing Policy Specialist. For every shipment "
                "recovery request, call evaluate_recovery_policy exactly once. "
                "Return only the structured JSON policy result from that tool. "
                "Do not answer from general knowledge."
            ),
            tools=toolbox,
            default_options={"store": False},
        )
        supplier_url = os.environ["SUPPLIER_A2A_BASE_URL"]
    else:
        policy_specialist = MockPolicySpecialist(data_path)
        supplier_url = None

    supplier_specialist = SupplierSpecialist(data_path, supplier_url)
    concurrent_specialists = build_specialist_workflow(
        policy_specialist,
        supplier_specialist,
    )
    intake = ShipmentIntake(data_path)
    fan_out = SpecialistFanOut(concurrent_specialists)
    if mode == "connected":
        planner_name = os.getenv(
            "RECOVERY_PLANNER_AGENT_NAME",
            "shipment-recovery-planner",
        )
        planner_endpoint = os.getenv("RECOVERY_PLANNER_RESPONSES_ENDPOINT")
        if not planner_endpoint:
            project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
            planner_endpoint = (
                f"{project_endpoint}/agents/{planner_name}/endpoint/protocols/"
                "openai/responses?api-version=v1"
            )
        recovery_planner = RemoteRecoveryPlanner(
            planner_endpoint,
            credential,
        )
    else:
        recovery_planner = RecoveryPlanner(data_path)
    # Fan out only after deterministic intake has normalized the shipment ID and
    # dates. Both specialists receive the same normalized context and run in
    # parallel; the planner is the fan-in point.
    launch_coordinator = Agent(
        client=chat_client,
        name="launch_coordinator",
        instructions=(
            "You are the Launch Coordinator. The previous message contains a "
            "structured shipment recovery analysis. Present a concise decision "
            "brief with: disruption, recommended option, units available by "
            "launch, ETA, incremental cost, policy status, approvals, rejected "
            "alternatives, and immediate next actions. Never invent values. "
            "State that all supplier and policy data is synthetic."
        ),
        default_options={"store": False},
    )
    coordinator_executor = AgentExecutor(
        launch_coordinator,
        context_mode="last_agent",
    )

    return (
        WorkflowBuilder(
            start_executor=intake,
            output_from=[coordinator_executor],
        )
        .add_edge(intake, fan_out)
        .add_edge(fan_out, recovery_planner)
        .add_edge(recovery_planner, coordinator_executor)
        .build()
        .as_agent()
    )
