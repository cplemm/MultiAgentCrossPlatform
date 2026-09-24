import json
from typing import Never

from agent_framework import AgentResponse, Executor, Message, WorkflowBuilder
from agent_framework import WorkflowContext, handler
from agent_framework_foundry_hosting import ResponsesHostServer
from dotenv import load_dotenv

from planner import build_plan


def _extract_payload(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Planner request contains no JSON object")
    return json.loads(text[start : end + 1])


class RecoveryPlannerAgent(Executor):
    @handler
    async def from_str(
        self,
        text: str,
        ctx: WorkflowContext[Never, AgentResponse],
    ) -> None:
        plan = build_plan(_extract_payload(text))
        await ctx.yield_output(
            AgentResponse(
                messages=[
                    Message(
                        "assistant",
                        [json.dumps(plan, ensure_ascii=True, sort_keys=True)],
                    )
                ]
            )
        )

    @handler
    async def from_messages(
        self,
        messages: list[Message],
        ctx: WorkflowContext[Never, AgentResponse],
    ) -> None:
        text = "\n".join(
            message.text for message in messages if message.text
        )
        await self.from_str(text, ctx)


def main() -> None:
    load_dotenv(override=False)
    planner = RecoveryPlannerAgent(id="recovery_planner")
    workflow = WorkflowBuilder(
        start_executor=planner,
        output_from=[planner],
    ).build()
    ResponsesHostServer(workflow.as_agent()).run()


if __name__ == "__main__":
    main()
