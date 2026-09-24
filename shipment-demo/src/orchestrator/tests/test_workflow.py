from typing import Never

from agent_framework import (
    AgentExecutorResponse,
    AgentResponse,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from shipment_workflow import RecoveryPlanner, ShipmentIntake, SpecialistFanOut
from specialists import (
    MockPolicySpecialist,
    SupplierSpecialist,
    build_specialist_workflow,
)


class CaptureCoordinator(Executor):
    def __init__(self):
        super().__init__(id="capture_coordinator")

    @handler
    async def run(
        self,
        prior: AgentExecutorResponse,
        ctx: WorkflowContext[Never, AgentResponse],
    ) -> None:
        await ctx.yield_output(
            AgentResponse(
                messages=[
                    Message(
                        "assistant",
                        [prior.agent_response.messages[-1].text],
                    )
                ]
            )
        )


async def test_mock_workflow_reaches_recovery_recommendation():
    data_path = "data/shipments.json"
    specialist_workflow = build_specialist_workflow(
        MockPolicySpecialist(data_path),
        SupplierSpecialist(data_path, None),
    )
    intake = ShipmentIntake(data_path)
    fan_out = SpecialistFanOut(specialist_workflow)
    planner = RecoveryPlanner(data_path)
    coordinator = CaptureCoordinator()
    workflow = (
        WorkflowBuilder(
            start_executor=intake,
            output_from=[coordinator],
        )
        .add_edge(intake, fan_out)
        .add_edge(fan_out, planner)
        .add_edge(planner, coordinator)
        .build()
    )

    events = await workflow.run("Analyze delayed shipment SHP-10042")
    output = events.get_outputs()[0]
    assert "Split incumbent + Alpine Energy" in output.messages[-1].text
