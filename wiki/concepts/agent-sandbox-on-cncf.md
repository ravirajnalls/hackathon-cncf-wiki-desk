---
title: Agent Sandbox on CNCF
summary: How CNCF projects provide secure, isolated runtime environments for AI agents at scale.
sources:
  - {video: "", t: 0, speaker: "Craig McLuckie (Stacklok)", year: "2026"}
  - {video: "aFX_6HL_i80", t: 0, speaker: "Xu Wang (Ant Group) & Yu Hu (JAPAN AI)", year: "2026"}
links: [agent-substrate, mecatl, kagent, cloud-native-agentic-standards]
updated: 2026-10-24
clarity_score: 0.0
---

# Agent Sandbox on CNCF

> How the CNCF ecosystem provides secure, isolated runtime environments for running AI agents at scale.

## The problem

AI agents need isolated environments to execute code, call tools, and interact with external systems — without risking the host or each other. Running one agent on a laptop is simple. Running hundreds or millions of agents in production requires a different architecture: isolated, governable, and resilient.

## CNCF projects addressing this

### Agent Substrate (Sandbox project)

A secure-by-default agent execution runtime designed for **running millions of sandboxes** on Kubernetes. Accepted as a CNCF Sandbox project in 2026.

- **774 contributors**, 130 contributing organizations, 5,716 GitHub stars (as of Oct 2026) [▶](https://github.com/agent-substrate/substrate)
- Designed for high-density, low-latency agent workloads
- Runs as a distributed system on Kubernetes
- Provides execution isolation without requiring a full VM per agent

### kagent + Agent Substrate integration

At KubeCon, Solo.io demonstrated running **sandboxed agents with kagent and Agent Substrate** — combining Kubernetes-native agent orchestration with the substrate's sandbox runtime. [▶](https://www.solo.io/blog/highlights-from-kubecon-cloudnativecon-north-america-2025)

### Mecatl — Cloud-Native Agent Harness

Open-sourced by Stacklok (Craig McLuckie, Sept 2026). A cloud-native agent harness built as a distributed system from the start:

- Separates the **agent loop** (reasoning, tool dispatch, permissions) from hosting, exposure, and security
- Supports terminal, API, and application clients against the same runtime
- Sessions survive worker failures (turn-level durability)
- Tool ecosystem governed through an explicit catalog with permission boundaries
- **Identity**: proposes SPIFFE trust domain encoding full delegation chain in JWT
- Resource: [github.com/stacklok/mecatl](https://github.com/stacklok/mecatl) | [mecatl.dev](https://mecatl.dev/)

### Cloud Native Agentic Standards (CNCF blog, Mar 2026)

The CNCF published guidance on cloud-native agentic patterns:
- Use **mTLS** to secure all inter-service and agent-tool communications
- Deploy agents in **isolated runtime environments** (containers, sandboxes)
- Treat prompts as supply-chain artifacts (versioned, signed, attributable)

Resource: [CNCF blog](https://www.cncf.io/blog/2026/03/23/cloud-native-agentic-standards/)

### Sandbox for Agentic Application (KubeCon talk)

**"Sandbox for Agentic Application With Cloud Native Stack"** — Xu Wang (Ant Group) & Yu Hu (JAPAN AI). Live demo of running agent sandboxes on a cloud-native stack at KubeCon. [▶](https://www.youtube.com/watch?v=aFX_6HL_i80)

## Key patterns

| Pattern | Implementation |
|---------|---------------|
| **Isolation** | Agent Substrate sandboxes, container runtimes |
| **Identity** | SPIFFE trust domains, JWT delegation chains |
| **Governance** | Mecatl tool catalog with permission boundaries |
| **Resilience** | Session state in durable storage, worker replaceability |
| **Scale** | Kubernetes-native, millions of sandboxes |

## Disagreements

> ⚠ The CNCF ecosystem is still converging on standards. Mecatl proposes one architecture (distributed harness with SPIFFE identity), while Agent Substrate focuses on the lower-level sandbox runtime. These are complementary but represent different layers of the stack. kagent + Agent Substrate integration shows one path; Mecatl shows another.
