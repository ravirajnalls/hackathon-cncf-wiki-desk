---
title: "kagent: AI agents on Kubernetes"
summary: How the CNCF Sandbox project kagent turns an AI agent (system prompt, model, tools) into a declarative Kubernetes resource, and when to use it versus hand-rolled agents or sandbox runtimes.
sources:
  - {video: "oXBr9UAOG2M", t: 0, speaker: "Eitan Yarmush (Solo.io)", year: "2025"}
  - {video: "-c1bmSr5328", t: 395, speaker: "Rajas Kakodkar (Broadcom)", year: "2026"}
links: [agent-sandbox-on-cncf, kubernetes-agent-sandbox, kata-containers-for-ai-agents]
updated: 2026-10-24
clarity_score: 0.0
---

# kagent: AI agents on Kubernetes

> kagent is the "agent as a Kubernetes resource" layer. [Agent Sandbox on CNCF](../../guides/agent-sandbox-on-cncf.md) covers where untrusted agent code runs; this page covers how agents are defined, wired to tools and operated.

## What it is

In plain language: an AI agent is a loop that asks an LLM what to do, lets it call tools, and repeats until the task is done. kagent lets you describe that agent in YAML and run it on your cluster like any other workload. The docs call it an open-source, Kubernetes-native runtime for AI agents, deployed and operated as first-class Kubernetes resources with the same CRDs, RBAC, GitOps and observability as other workloads [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/). It was accepted into CNCF on May 22, 2025 at the Sandbox level [docs](https://www.cncf.io/projects/kagent/), and was created at Solo.io [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/).

Eitan Yarmush (Solo.io, kagent maintainer) boils an agent down to three things: a system prompt, an LLM, and tools [▶ 00:00](https://www.youtube.com/watch?v=oXBr9UAOG2M&t=0s).

## How it works

- **The agent loop.** The user's message gets the system prompt appended and goes to the LLM, which decides whether to call tools; if it needs more, it keeps going, otherwise it answers [▶ 00:43](https://www.youtube.com/watch?v=oXBr9UAOG2M&t=43s). Rajas Kakodkar (Broadcom) describes the same thing as essentially an infinite for loop around the LLM, with tools it can use to act [▶ 06:35](https://www.youtube.com/watch?v=-c1bmSr5328&t=395s).
- **Tools via MCP.** Yarmush calls MCP "sort of like the USB of tool connection", and notes that essentially every project now ships an MCP server [▶ 00:43](https://www.youtube.com/watch?v=oXBr9UAOG2M&t=43s). In kagent, tools are MCP-style functions, with pre-built ones such as showing pod logs and querying Prometheus [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/).
- **Declarative API.** Because an agent is just declarative, Solo asked why it couldn't run in Kubernetes like every other workload and came up with an API for agents connected to tools [▶ 01:27](https://www.youtube.com/watch?v=oXBr9UAOG2M&t=87s). A model config, a system prompt and a list of tools in YAML is then a complete agent [▶ 02:10](https://www.youtube.com/watch?v=oXBr9UAOG2M&t=130s).
- **Three components.** The docs name Tools, Agents (which plan, execute and analyze, and can be grouped into teams with a planning agent) and a Framework to run them via UI or declaratively [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/).
- **Platform features.** Agent lifecycle via CRDs and GitOps, Go and Python ADK runtimes, bring-your-own frameworks (LangGraph, CrewAI, Google ADK), vector-backed long-term memory, and human-in-the-loop approval gates, installed with a single helm install [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/).

## When to use it vs alternatives

- **Use kagent** when platform/DevOps teams want agents for cluster operations (connectivity diagnosis, Prometheus alerts, Gateway/HTTPRoute debugging, Argo Rollouts) managed with the GitOps and RBAC they already have [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/).
- **Hand-rolled agent script.** Kakodkar builds a minimal agent from scratch in his 101 talk, as a learning exercise rather than the production path; for production he points to VPC endpoints, self-hosted models, API gateways and agent memory [▶ 22:40](https://www.youtube.com/watch?v=-c1bmSr5328&t=1360s).
- **Isolation is a separate concern.** kagent defines and runs agents; it does not by itself give each agent a separate kernel. For that, pair it with a sandbox runtime: see [Kubernetes Agent Sandbox](../kubernetes/agent-sandbox.md) and [Kata Containers for AI agents](../../related-runtimes/kata-containers-for-ai-agents.md). Kakodkar lists kagent, Kubernetes SIGs agent sandbox and agent gateway as related efforts for the multi-cluster, multi-agent context [▶ 24:51](https://www.youtube.com/watch?v=-c1bmSr5328&t=1491s).

## Real-world usage

- **DNB (Norway's largest financial services group)**: the platform team running payments built an internal assistant on kagent and agentgateway, starting as a Slack bot, with MCP servers for DB2 inspection (structures, lock reports, performance data), MQ, Jira and Atlassian; agentgateway ties into Microsoft Entra ID with JWT identity propagation. The goal was supporting more users without adding headcount; adoption was faster than expected, and the team has moved to contributing a security-enhancement design proposal. No user counts or time-saved figures are given [docs](https://kagent.dev/blog/dnb-kagent-agentgateway).
- **Community member Maryam Naveed (Kotaicode publication)**: a self-healing nginx setup where kagent plus the Khook event hook detects pod crashes and config problems, fixes nginx config, SSL and syntax errors, and verifies recovery. The write-up claims remediation now takes about 30 seconds instead of hours of manual SSH, log parsing and ConfigMap editing; cluster size and incident volume are not given, and the employer is not named [docs](https://www.kagent.dev/blog/community-nginx-khook-kagent).

> Only two independently named end-user use cases were found, both from kagent.dev case-study posts; the project keeps no ADOPTERS.md or USERS.md (both 404), and the end-user talks found were demos or did not mention kagent.

## Disagreements

> ⚠ Sources differ on kagent's underlying framework. The April 2025 CNCF launch post says kagent is built on Microsoft's AutoGen [docs](https://www.cncf.io/blog/2025/04/15/kagent-bringing-agentic-ai-to-cloud-native/), while the current docs say the framework is built on Google's ADK [docs](https://kagent.dev/docs/kagent/0.x/introduction/what-is-kagent/). Treat the docs as current; the blog reflects the early design.
