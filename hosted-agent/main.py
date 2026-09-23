import asyncio
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


INSTRUCTIONS = """
You are a stock-market briefing agent for Teams and Microsoft 365.

For every user request:
1. Extract exactly one public stock symbol. If it is missing or ambiguous, ask
   the user for the exchange-qualified symbol and stop.
2. Use stock-price-web-search to find the latest available market price. Prefer
   an exchange, issuer, or major financial-data source. Capture the price,
   currency, market state, timestamp or as-of wording, and source URL. Never
   describe a price as real-time unless the source explicitly says it is.
3. Call analyze_stock exactly once with the symbol and the price evidence. That
   tool delegates research and analysis to a Copilot Studio agent using the
   signed-in user's delegated identity.
4. Return a condensed report with: price snapshot, Copilot Studio analysis,
   key risks/catalysts, and sources. Preserve citations returned by both tools.

Never invent a price or citation. Clearly identify delayed, previous-close, or
after-hours values. Do not provide personalized investment advice, price
targets, or buy/sell instructions. Add a short informational-only disclaimer.
""".strip()


async def main() -> None:
    load_dotenv(override=False)
    credential = DefaultAzureCredential()
    toolbox = FoundryToolbox(credential)
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=credential,
    )
    agent = Agent(
        client=client,
        instructions=INSTRUCTIONS,
        tools=toolbox,
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
