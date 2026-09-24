import argparse
import json
import os

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential


parser = argparse.ArgumentParser()
parser.add_argument(
    "--input",
    default="Who am I? Verify my delegated identity.",
)
parser.add_argument("--previous-response-id")
args = parser.parse_args()

project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=AzureCliCredential(),
)
openai = project.get_openai_client()
kwargs = {
    "input": args.input,
    "extra_body": {
        "agent_reference": {
            "name": os.environ["FOUNDRY_CALLER_AGENT_NAME"],
            "type": "agent_reference",
        }
    },
}
if args.previous_response_id:
    kwargs["previous_response_id"] = args.previous_response_id

response = openai.responses.create(**kwargs)
result = {
    "id": response.id,
    "status": response.status,
    "output_text": response.output_text,
    "outputs": [],
}
for item in response.output:
    entry = {"type": item.type}
    consent_link = getattr(item, "consent_link", None)
    if consent_link:
        entry["consent_link"] = consent_link
    result["outputs"].append(entry)
print(json.dumps(result, indent=2))

