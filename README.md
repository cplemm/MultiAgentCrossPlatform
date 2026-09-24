# 🔗 Multi-Agent Cross-Platform Demos

This repository demonstrates how AI agents built on different Microsoft
platforms (via low-code in Copilot Studio or pro-code in Microsoft Foundry) or even non-Microsoft systems (via A2A) can collaborate, while preserving the identity and permissions of the
signed-in user.

The scenarios focus on agent-to-agent delegation across **Microsoft Foundry**,
**Copilot Studio**, and **Azure Container Apps** (as an easy to test hosting environment for external A2A agents). They show
how protocols such as **A2A**, **MCP**, **OAuth 2.0**, and the **Microsoft Entra
on-behalf-of flow** (OBO) can be combined without passing raw user tokens into agent
code.

## 🎯 What these demos cover

- 🤝 Delegating work between agents hosted on different platforms
- 👤 Preserving the signed-in user's identity across trust boundaries
- 🔐 Applying delegated OAuth, Microsoft Entra ID, OBO, and Azure RBAC
- 🔌 Connecting agents through A2A, MCP, and platform-specific protocols
- 🧭 Understanding where authentication, authorization, and token exchange occur

These samples are intended for learning, architecture exploration, and
demonstration. Each scenario includes its own deployment instructions,
architecture diagrams, prerequisites, and limitations.

## 🧪 Demo scenarios

| Scenario | Direction | Integration | Main identity pattern |
| --- | --- | --- | --- |
| 📈 [Foundry stock agent with Copilot Studio analysis](./foundry-cps-stock-agent/README.md) | Foundry → Copilot Studio | Authenticated MCP bridge | Foundry delegates to a bridge, which uses OBO to call Copilot Studio as the user |
| 🔗 [Copilot Studio with a Foundry market-research agent](./cps-foundry-a2a-agent/README.md) | Copilot Studio → Foundry | A2A 1.0 | Copilot Studio obtains a delegated Foundry token and Foundry enforces user RBAC |
| 🌐 [Foundry calling an external A2A agent](./foundry-external-a2a-agent/README.md) | Foundry → External agent → Microsoft Graph | A2A 1.0 | Foundry brokers a delegated API token and the external agent performs OBO for Graph |

### 📈 Scenario 1: Foundry to Copilot Studio

A Foundry Hosted Agent creates a stock briefing by combining Foundry Web Search
with analysis from a Copilot Studio agent. An OAuth-protected MCP bridge connects
the platforms and performs OBO for the Power Platform audience.

➡️ [Open the Foundry-to-Copilot Studio demo](./foundry-cps-stock-agent/README.md)

### 🔗 Scenario 2: Copilot Studio to Foundry

A Copilot Studio agent delegates market research to a Foundry Prompt Agent over
an authenticated A2A endpoint. The delegated token represents the signed-in
user, and Foundry authorizes access through Azure RBAC.

➡️ [Open the Copilot Studio-to-Foundry demo](./cps-foundry-a2a-agent/README.md)

### 🌐 Scenario 3: Foundry to an external A2A agent

A Foundry Prompt Agent calls an external Python A2A agent hosted on Azure
Container Apps. The external agent validates the delegated token, performs an
OBO exchange, and calls Microsoft Graph `/me` for the same user.

➡️ [Open the Foundry-to-external-A2A demo](./foundry-external-a2a-agent/README.md)

## 🧭 Choosing a scenario

- Use **Scenario 1** to understand MCP-based integration with Copilot Studio and
  a dedicated OBO bridge.
- Use **Scenario 2** to explore direct A2A delegation from Copilot Studio
  to a Foundry Prompt Agent.
- Use **Scenario 3** to learn how Foundry can securely delegate to an
  independently hosted A2A service and downstream API.

## ⚠️ Before deploying

The demos use capabilities whose availability, portal experience, and protocol
support can evolve. Review the prerequisites and limitations in the selected
scenario README before provisioning Azure or Microsoft 365 resources.
