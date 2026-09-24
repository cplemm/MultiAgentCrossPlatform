import asyncio
import os

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest


async def main() -> None:
    base_url = os.environ["EXTERNAL_A2A_BASE_URL"].rstrip("/")
    token = os.environ["A2A_ACCESS_TOKEN"]

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(120.0),
    ) as http_client:
        resolver = A2ACardResolver(
            httpx_client=http_client,
            base_url=base_url,
            agent_card_path=".well-known/agent-card.json",
        )
        card = await resolver.get_agent_card()
        client = await create_client(
            agent=card,
            client_config=ClientConfig(
                streaming=False,
                httpx_client=http_client,
            ),
        )
        request = SendMessageRequest(
            message=new_text_message(
                "Who am I? Verify my delegated identity.",
                role=Role.ROLE_USER,
            )
        )
        received = False
        async for response in client.send_message(request):
            print(response)
            received = True
        await client.close()
        if not received:
            raise RuntimeError("The A2A agent returned no response")


if __name__ == "__main__":
    asyncio.run(main())
