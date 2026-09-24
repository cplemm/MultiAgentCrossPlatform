import os

from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from shipment_workflow import build_workflow_agent


def main() -> None:
    load_dotenv(override=False)
    credential = DefaultAzureCredential()
    chat_client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=credential,
    )
    toolbox = (
        FoundryToolbox(credential)
        if os.getenv("SHIPMENT_DEMO_MODE", "mock").lower() == "connected"
        else None
    )
    workflow_agent = build_workflow_agent(
        chat_client,
        toolbox,
        credential,
    )
    ResponsesHostServer(workflow_agent).run()


if __name__ == "__main__":
    main()
