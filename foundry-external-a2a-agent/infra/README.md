# Infrastructure approach

This demo intentionally combines two supported automation surfaces:

- `azure.yaml` with the Microsoft Foundry provider provisions the Foundry
  account/project and model deployment.
- `az containerapp up --source` builds and deploys the external A2A agent,
  including its Container Apps environment and registry.

The root `scripts/deploy.ps1` orchestrates both surfaces and then creates the
OAuth `RemoteA2A` connection and Prompt Agent through supported CLI/SDK APIs.

