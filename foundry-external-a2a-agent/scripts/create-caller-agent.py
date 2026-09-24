import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    A2AProtocolVersion,
    A2ATool,
    PromptAgentDefinition,
)
from azure.identity import AzureCliCredential


project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini")
connection_name = os.getenv(
    "EXTERNAL_A2A_CONNECTION_NAME",
    "external-graph-profile-oauth",
)
external_base_url = os.environ["EXTERNAL_A2A_BASE_URL"]
agent_name = os.getenv(
    "FOUNDRY_CALLER_AGENT_NAME",
    "external-profile-orchestrator",
)

project = AIProjectClient(
    endpoint=project_endpoint,
    credential=AzureCliCredential(),
)
connection = project.connections.get(connection_name)
tool = A2ATool(
    a2a_version=A2AProtocolVersion.V1_0,
    base_url=external_base_url,
    project_connection_id=connection.id,
)
agent = project.agents.create_version(
    agent_name=agent_name,
    definition=PromptAgentDefinition(
        model=model,
        instructions=(
            "You demonstrate delegated cross-platform agent communication. "
            "When the user asks who they are, asks for their profile, or asks "
            "you to verify delegated identity, always call the external A2A "
            "agent. Explain that the external agent used OAuth delegation and "
            "OBO to Microsoft Graph. Do not invent profile fields."
        ),
        tools=[tool],
    ),
    description=(
        "Calls an external Azure Container Apps A2A agent using per-user OAuth."
    ),
)
print(f"Created {agent.name}, version {agent.version}")
