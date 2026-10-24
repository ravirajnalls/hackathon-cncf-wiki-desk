---
title: Securing MCP tool calls in agent sandboxes
summary: How to control what an AI agent may do through MCP, by combining sandboxed tool servers, gateway-level authentication, and default-deny per-tool authorization.
sources:
  - {video: "tEAkoZpdhSc", t: 0, speaker: "Nina Polshakova (Solo.io) & Luc Chmielowski (Kyverno)", year: "2026"}
  - {video: "KXmPxmNN0fc", t: 0, speaker: "Haiyan Meng (Google) & Evaline Ju (IBM)", year: "2026"}
  - {video: "vi_VhZLWs9k", t: 0, speaker: "Mingshan Zhao & Zhen Zhang (Alibaba)", year: "2026"}
  - {video: "n_i9w_wgD7I", t: 0, speaker: "Cosmonic (wasmCloud Sandbox MCP)", year: "2025"}
links: [agent-sandbox-on-cncf, kubernetes-agent-sandbox, kagent-ai-agents-on-kubernetes, kata-containers-for-ai-agents, gvisor-for-ai-agent-isolation]
updated: 2026-10-24
clarity_score: 0.0
---

# Securing MCP tool calls in agent sandboxes

> A sandbox stops code from escaping. It does not decide *which tools an agent may call*. That second job needs its own layer.

## What it is

The Model Context Protocol (MCP) is how an AI agent discovers and calls tools such as "list pods" or "run this code". An [agent sandbox](agent-sandbox-on-cncf.md) isolates the runtime, but every MCP tool call is still a request that can do real damage: apply a manifest to production, leak customer data, or run untrusted code. Securing MCP tool calls means putting controls on three things: **who the caller is**, **which tools they may call**, and **where the tool itself runs**.

## Why the protocol alone is not enough

MCP is a JSON-RPC protocol with an added semantic layer so the LLM knows what each tool does; authorization is something you implement yourself inside each MCP server, so results vary with whoever wrote the server [▶ 02:47](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=167s). For a platform team this means audit trails in many places and duplicated authorization logic [▶ 03:32](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=212s).

The demo failure case: an agent has direct access to every tool, no auth is in place, a generated manifest gets applied, and prod goes down [▶ 09:22](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=562s). The Cosmonic talk adds the supply-chain side: the news is full of exploited, poorly implemented MCP servers, and a typical container image bundles an entire Linux distribution that becomes part of the attack chain [▶ 01:39](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=99s).

## How it works: four layers

### 1. Put a gateway in front of the tools

Route all agent-to-tool traffic through a gateway so authentication and authorization happen once, not per server. Agent Gateway implements the MCP OAuth 2.0 flow, so agents get delegated, scoped, revocable access without each MCP server implementing it [▶ 07:54](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=474s). The Kubernetes agentic networking sub-project does the same with new experimental Gateway API extensions: an `XBackend` that defines the MCP backend and an `XAccessPolicy` that can target a backend or a gateway [▶ 03:36](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=216s).

### 2. Authenticate the caller

In the Solo/Kyverno demo the client must complete an OAuth 2.0 login through Keycloak before it can even connect, and the user then holds a token [▶ 10:07](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=607s). In agentic networking the agent identity is a Kubernetes service account or a SPIFFE ID [▶ 05:46](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=346s).

### 3. Authorize each tool call, default deny

- **Tool allow lists.** Without a gateway the agent can reach every tool on both MCP servers [▶ 02:51](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=171s). The platform engineer's first step is to deny by default; an access policy with an empty tool allow list blocked the agent's calls [▶ 13:26](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=806s). Tools are then added one by one: the demo allowed one tool and still denied `echo` [▶ 14:10](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=850s). Deny lists are on the roadmap [▶ 23:54](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1434s).
- **External authorization with a policy engine.** Agent Gateway supports the same external authorization spec as Envoy, so Kyverno works with it out of the box [▶ 05:43](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=343s). Kyverno added an MCP CEL library so a policy can read the method, the tool name and typed arguments from the request [▶ 21:46](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=1306s).
- **Reuse existing authorization.** Rather than rebuild a permission model, the policy asks Kubernetes whether the user may touch the resource named in the tool arguments, because Kubernetes already does authorization well [▶ 23:11](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=1391s). The speakers' conclusion: native MCP auth might not be enough for the enterprise, and an existing policy engine can bridge the gap [▶ 25:23](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=1523s).

### 4. Sandbox where the tool runs

- **Capability-based Wasm.** The Sandbox MCP approach deploys MCP servers as WebAssembly components that only get the minimal system calls they need, in deny-by-default sandboxes [▶ 02:30](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=150s). Components are small enough to start instantly and scale to zero [▶ 03:15](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=195s). It deploys to Kubernetes with a Helm template [▶ 04:51](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=291s).
- **Container sandboxes behind a gateway.** Alibaba's OpenKruise agent sandbox exposes code and command tools through MCP and an E2B-compatible API [▶ 20:30](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1230s). Because the code may come from malicious prompts, it uses a secure container runtime plus network policy so all incoming traffic must come from the sandbox gateway [▶ 21:56](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1316s). MCP sessions are mapped to sandboxes, which are cleaned up when the session expires [▶ 21:14](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1274s). For secrets, the LLM API key is injected into the sandbox through a file-system API instead of being kept by the agent [▶ 19:03](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1143s). For the runtimes themselves see [Kata Containers](../related-runtimes/kata-containers-for-ai-agents.md), [gVisor](../related-runtimes/gvisor-for-ai-agent-isolation.md) and the [Kubernetes Agent Sandbox](../projects/kubernetes/agent-sandbox.md).

### Filtering and audit (emerging)

Agents could validate their own inputs and outputs, but, as with container networking, the speakers argue you cannot rely on every agent to do so. Example: a request that quietly asks for all customers with contract numbers may be data exfiltration [▶ 22:27](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1347s). A tool response can also carry an injected instruction, such as "email this address", that the agent would happily follow [▶ 23:11](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1391s). The AI gateway working group has a payload processing proposal to standardize this filtering [▶ 23:54](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1434s). For audit, the group proposes tracing with OpenTelemetry GenAI conventions so you can see why a call was denied; this is a provisional proposal, not yet implemented [▶ 15:49](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=949s).

## When to use which

| Need | Approach |
|------|----------|
| Third-party or untrusted MCP servers | Run them in a capability-based sandbox (Wasm) or a VM/user-space-kernel runtime |
| Stop an agent calling dangerous tools | Gateway + default-deny tool allow list |
| Rules depend on tool arguments (e.g. target namespace) | External authorization with a policy engine such as Kyverno |
| Many short-lived agents running code | Per-session sandboxes behind a sandbox gateway |

These layers stack. Sandbox isolation limits blast radius if a tool is compromised; gateway policy limits which tools get called at all.

## Real-world usage

- Solo.io and Kyverno maintainers demoed Agent Gateway + Kyverno in front of kagent's Kubernetes tools, blocking a manifest apply to a production namespace while still allowing read tools [▶ 10:50](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=650s). See [kagent](../projects/kagent/index.md).
- Alibaba exposes sandbox code execution to reinforcement-learning jobs through MCP [▶ 19:03](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1143s).

## Disagreements

> ⚠ **Where to enforce.** The Kyverno talk puts argument-aware policy in an external authorizer behind the gateway [▶ 05:43](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=343s), while the agentic networking API centres on declarative per-tool allow lists in the access policy, with external auth as an option [▶ 06:30](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=390s). The Cosmonic talk instead shrinks the tool server's own capabilities. These are complementary rather than exclusive, but there is no single agreed model yet; the networking APIs are explicitly experimental.

## References

**Talks**

1. [Nina Polshakova (Solo.io) & Luc Chmielowski (Kyverno), 2026](https://www.youtube.com/watch?v=tEAkoZpdhSc), cited at [02:47](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=167s), [03:32](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=212s), [05:43](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=343s), [07:54](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=474s), [09:22](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=562s), [10:07](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=607s), [10:50](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=650s), [21:46](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=1306s), [23:11](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=1391s), [25:23](https://www.youtube.com/watch?v=tEAkoZpdhSc&t=1523s)
2. [Cosmonic (wasmCloud Sandbox MCP), 2025](https://www.youtube.com/watch?v=n_i9w_wgD7I), cited at [01:39](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=99s), [02:30](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=150s), [03:15](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=195s), [04:51](https://www.youtube.com/watch?v=n_i9w_wgD7I&t=291s)
3. [Haiyan Meng (Google) & Evaline Ju (IBM), 2026](https://www.youtube.com/watch?v=KXmPxmNN0fc), cited at [02:51](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=171s), [03:36](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=216s), [05:46](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=346s), [06:30](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=390s), [13:26](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=806s), [14:10](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=850s), [15:49](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=949s), [22:27](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1347s), [23:11](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1391s), [23:54](https://www.youtube.com/watch?v=KXmPxmNN0fc&t=1434s)
4. [Mingshan Zhao & Zhen Zhang (Alibaba), 2026](https://www.youtube.com/watch?v=vi_VhZLWs9k), cited at [19:03](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1143s), [20:30](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1230s), [21:14](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1274s), [21:56](https://www.youtube.com/watch?v=vi_VhZLWs9k&t=1316s)
