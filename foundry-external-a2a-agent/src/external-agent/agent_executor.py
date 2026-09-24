import json
import logging

import httpx

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState

from auth import EntraTokenVerifier, extract_bearer_token
from obo import GraphOboClient, OboExchangeError


logger = logging.getLogger(__name__)


class GraphProfileAgentExecutor(AgentExecutor):
    def __init__(
        self,
        verifier: EntraTokenVerifier,
        graph_obo: GraphOboClient,
    ) -> None:
        self._verifier = verifier
        self._graph_obo = graph_obo

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = (
            context.current_task
            if context.current_task
            else new_task_from_user_message(context.message)
        )
        if not context.current_task:
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message(
                "Validating delegated identity and calling Microsoft Graph..."
            ),
        )

        try:
            headers = context.call_context.state.get("headers", {})
            assertion = extract_bearer_token(headers.get("authorization"))
            claims = await self._verifier.verify(assertion)
            graph_token = await self._graph_obo.acquire_graph_token(assertion)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    params={
                        "$select": (
                            "id,displayName,userPrincipalName,mail,"
                            "jobTitle,department"
                        )
                    },
                    headers={"Authorization": f"Bearer {graph_token}"},
                )
                response.raise_for_status()
                profile = response.json()

            request_text = get_message_text(context.message) or "Who am I?"
            result = {
                "message": (
                    "Delegated identity confirmed by the external A2A agent. "
                    "The profile was retrieved from Microsoft Graph using OBO."
                ),
                "request": request_text[:500],
                "incoming_token": {
                    "tenant_id": claims.get("tid"),
                    "object_id": claims.get("oid"),
                    "subject": claims.get("sub"),
                    "scopes": str(claims.get("scp", "")).split(),
                },
                "graph_profile": profile,
            }
            artifact_text = json.dumps(
                result,
                indent=2,
                ensure_ascii=True,
            )

            await updater.add_artifact(
                parts=[
                    new_text_part(
                        text=artifact_text,
                        media_type="application/json",
                    )
                ]
            )
            await updater.update_status(
                state=TaskState.TASK_STATE_COMPLETED,
                message=new_text_message(
                    "Delegated Microsoft Graph profile retrieved successfully."
                ),
            )
            logger.info(
                "Completed delegated profile request task_id=%s oid=%s",
                task.id,
                claims.get("oid", "unknown"),
            )
        except (OboExchangeError, httpx.HTTPError) as error:
            logger.warning(
                "Delegated downstream call failed task_id=%s type=%s",
                task.id,
                type(error).__name__,
            )
            await updater.update_status(
                state=TaskState.TASK_STATE_FAILED,
                message=new_text_message(
                    "The external agent could not complete delegated OBO."
                ),
            )
        except Exception as error:
            logger.exception(
                "A2A request failed task_id=%s type=%s",
                task.id,
                type(error).__name__,
            )
            await updater.update_status(
                state=TaskState.TASK_STATE_FAILED,
                message=new_text_message(
                    "The external agent could not validate or process the request."
                ),
            )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise NotImplementedError("Cancellation is not supported in this demo")

