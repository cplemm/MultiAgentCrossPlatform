import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, WebSearchTool
from azure.identity import AzureCliCredential


PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini")
AGENT_NAME = os.getenv("FOUNDRY_AGENT_NAME", "market-research-agent")

INSTRUCTIONS = """
You are a financial-market research specialist called by another agent over A2A.

For stock-market questions:
1. Use web search for current public information.
2. State the latest price you can verify, its currency, market state, and as-of
   time. Never describe delayed information as real-time.
3. Summarize recent material news, catalysts, and risks.
4. Include source links and distinguish facts from interpretation.

Keep the result under 450 words. Do not provide personalized investment advice,
price targets, or buy/sell recommendations.
""".strip()


project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=AzureCliCredential(),
)

agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model=MODEL,
        instructions=INSTRUCTIONS,
        tools=[WebSearchTool()],
    ),
    description="Researches current financial-market information.",
)

print(f"Created {agent.name}, version {agent.version}")
