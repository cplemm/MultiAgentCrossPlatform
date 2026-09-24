from __future__ import annotations

import json
import os
from typing import Any

import httpx
from agent_framework import (
    Agent,
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentResponse,
    Executor,
    Message,
    WorkflowContext,
    handler,
)
from agent_framework.orchestrations import ConcurrentBuilder

from domain import as_json, load_demo_data, resolve_shipment


def _last_text(messages: list[Message]) -> str:
    return next(
        (message.text for message in reversed(messages) if message.text),
        "",
    )


def _parse_json_text(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            return {"raw": text}
        return json.loads(text[start : end + 1])


def extract_supplier_payload(response: dict[str, Any]) -> dict[str, Any]:
    if "error" in response:
        raise RuntimeError(
            response["error"].get("message", "Supplier A2A call failed")
        )
    result = response["result"]
    task = result.get("task", result)
    artifact_text = "".join(
        part.get("text", "")
        for artifact in task.get("artifacts", [])
        for part in artifact.get("parts", [])
    )
    if not artifact_text:
        raise RuntimeError("Supplier A2A agent returned no artifact text")
    return json.loads(artifact_text)


class MockPolicySpecialist(Executor):
    def __init__(self, data_path: str, id: str = "purchasing_policy_specialist"):
        super().__init__(id=id)
        self._data_path = data_path

    @handler
    async def run(
        self,
        request: AgentExecutorRequest,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        data = load_demo_data(self._data_path)
        payload = {
            "specialist": self.id,
            "policy": data["mock_policy"],
        }
        response = AgentResponse(
            messages=[Message("assistant", [as_json(payload)])]
        )
        await ctx.send_message(
            AgentExecutorResponse(
                self.id,
                response,
                full_conversation=list(request.messages) + list(response.messages),
            )
        )


class SupplierSpecialist(Executor):
    def __init__(
        self,
        data_path: str,
        base_url: str | None,
        id: str = "supplier_specialist",
    ):
        super().__init__(id=id)
        self._data_path = data_path
        self._base_url = base_url.rstrip("/") if base_url else None

    async def _invoke_remote(self, prompt: str) -> dict[str, Any]:
        timeout = float(os.getenv("SUPPLIER_A2A_TIMEOUT_SECONDS", "45"))
        request_id = "shipment-supplier"
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": request_id,
                    "role": "ROLE_USER",
                    "parts": [{"text": prompt}],
                }
            },
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self._base_url,
                json=body,
                headers={"A2A-Version": "1.0"},
            )
            response.raise_for_status()
        return extract_supplier_payload(response.json())

    @handler
    async def run(
        self,
        request: AgentExecutorRequest,
        ctx: WorkflowContext[AgentExecutorResponse],
    ) -> None:
        prompt = _last_text(list(request.messages))
        if self._base_url:
            supplier_payload = await self._invoke_remote(prompt)
        else:
            data = load_demo_data(self._data_path)
            shipment = resolve_shipment(prompt, data)
            supplier_payload = {
                "shipment_id": shipment.shipment_id,
                "part_number": shipment.part_number,
                "offers": data["mock_supplier_offers"],
            }
        payload = {"specialist": self.id, "supplier": supplier_payload}
        response = AgentResponse(
            messages=[Message("assistant", [as_json(payload)])]
        )
        await ctx.send_message(
            AgentExecutorResponse(
                self.id,
                response,
                full_conversation=list(request.messages) + list(response.messages),
            )
        )


async def aggregate_specialists(
    results: list[AgentExecutorResponse],
) -> str:
    payload: dict[str, Any] = {"specialists": {}}
    for result in results:
        messages = result.agent_response.messages
        text = messages[-1].text if messages else "{}"
        parsed = _parse_json_text(text)
        payload["specialists"][result.executor_id] = parsed
    return as_json(payload)


def build_specialist_workflow(
    policy_agent: Agent | Executor,
    supplier_agent: Executor,
):
    return (
        ConcurrentBuilder(
            participants=[policy_agent, supplier_agent],
        )
        .with_aggregator(aggregate_specialists)
        .build()
    )
