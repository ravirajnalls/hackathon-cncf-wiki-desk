---
title: Agent Sandbox on CNCF
summary: How CNCF projects provide secure, isolated runtime environments for AI agents at scale.
sources:
  - {video: "aFX_6HL_i80", t: 0, speaker: "Xu Wang (Ant Group) & Yu Hu (JAPAN AI)", year: "2026"}
  - {video: "", t: 0, speaker: "Craig McLuckie (Stacklok)", year: "2026"}
  - {video: "", t: 0, speaker: "Rahul Jadhav (Accuknox)", year: "2025"}
links: [agent-substrate, mecatl, kagent, kata-containers, cloud-native-agentic-standards]
updated: 2026-10-24
clarity_score: 0.0
---

# Agent Sandbox on CNCF

> How the CNCF ecosystem provides secure, isolated runtime environments for AI agents at scale.

## What is an agent sandbox?

An agent sandbox is an isolated runtime environment where AI agents execute code, call tools, and process data — without risking the host or other tenants. At enterprise scale, sandboxes must enforce **strong isolation** (separate kernels), **data boundaries** (no cross-tenant leaks), and **fast startup** (seconds, not minutes).

## The two defining ideas

Xu Wang and Yu Hu (Ant Group / Japan AI) presented the foundational thinking at KubeCon [▶ 05:50](https://www.youtube.com/watch?v=aFX_6HL_i80&t=350s):

1. **Lifecycle** — A sandbox has a full lifecycle: create, configure, execute, observe, reset and destroy. A sandbox is not just a pod; the pod is one object in that lifecycle. [▶ 05:50](https://www.youtube.com/watch?v=aFX_6HL_i80&t=350s)
2. **Strong isolation** — Needs a separate kernel. "Name space and the C group isolated. It does not satisfy our requirements. Because the container use the same kernel." [▶ 07:18](https://www.youtube.com/watch?v=aFX_6HL_i80&t=438s)

## Why containers aren't enough

Containers share the host kernel. Xu Wang explains: "If untrusted code exploits the kernel, it will just affect all the containers." Their solution: **VM-based sandboxes** where each sandbox gets its own guest kernel. [▶ 7:57](https://www.youtube.com/watch?v=aFX_6HL_i80&t=477s)

Trade-off: "It will take more startup time and more memory. But this kind of overhead should be solved by the technology." [▶ 8:51](https://www.youtube.com/watch?v=aFX_6HL_i80&t=531s)

## Real-world architecture (Japan AI)

Xu Wang's team built a production agent sandbox on open source:
- **Kata Containers** — VM-backed container runtime (Open Infra Foundation project) [▶ 12:28](https://www.youtube.com/watch?v=aFX_6HL_i80&t=748s)
- **containerd + KVM** — container runtime and hypervisor [▶ 11:45](https://www.youtube.com/watch?v=aFX_6HL_i80&t=705s)
- **Nydus + Dragonfly** — image distribution for fast startup [▶ 15:22](https://www.youtube.com/watch?v=aFX_6HL_i80&t=922s)
- **Kubernetes** — orchestration of sandbox resources [▶ 13:13](https://www.youtube.com/watch?v=aFX_6HL_i80&t=793s)

Result: full environment setup in **1 minute 40 seconds** from scratch. [▶ 21:30](https://www.youtube.com/watch?v=aFX_6HL_i80&t=1290s)

## Security boundaries

For multi-tenant agent serving, data isolation is critical: "There is a lot of user sensitive data. We must make sure it never leaks to other users, other tenants." [▶ 3:37](https://www.youtube.com/watch?v=aFX_6HL_i80&t=217s)

SaaS sandboxes offer a quick win but introduce risk: "The data is leaving our control." [▶ 5:05](https://www.youtube.com/watch?v=aFX_6HL_i80&t=305s)

## Sandboxing with LSM-BPF

Rahul Jadhav (Accuknox) presented at KubeCon India 2025 on using **Linux Security Modules + BPF** to sandbox agentic AI at the kernel level — enforcing security policies via eBPF programs without full VM overhead. [▶](https://confpad.io/conferences/kubecon-cloudnativecon-india-2025/sandboxing-agentic-ai-with-lsm-bpf)

## CNCF projects in the stack

### Agent Substrate (Sandbox project)

A secure-by-default agent execution runtime for **running millions of sandboxes** on Kubernetes. Accepted as a CNCF Sandbox project in 2026. [▶](https://github.com/agent-substrate/substrate)

- 774 contributors, 130 contributing organizations, 5,716 GitHub stars
- Designed for high-density, low-latency agent workloads
- Provides execution isolation without requiring a full VM per agent

### kagent (CNCF)

An open source programming framework for running AI agents in Kubernetes. Accepted May 2025. Paired with Agent Substrate for sandboxed agent execution. [▶](https://www.cncf.io/projects/kagent/)

### Mecatl (Stacklok)

Cloud-native agent harness built as a distributed system. Separates the agent loop from hosting and security. Supports SPIFFE identity, tool catalogs, and turn-level session durability. [▶](https://github.com/stacklok/mecatl)

## Key patterns

| Pattern | Implementation |
|---------|---------------|
| **Isolation** | VM-based sandboxes (Kata), LSM-BPF, Agent Substrate |
| **Identity** | SPIFFE trust domains, JWT delegation chains (Mecatl) |
| **Governance** | Tool catalogs with permission boundaries |
| **Resilience** | Session state in durable storage, worker replaceability |
| **Scale** | Kubernetes-native, millions of sandboxes |
| **Startup** | Nydus/Dragonfly image distribution, < 2 min provisioning |

## Disagreements

> ⚠ Two schools of thought exist on isolation strength. Xu Wang advocates VM-based isolation ("containers use the same kernel") while Rahul Jadhav advocates kernel-level enforcement via LSM-BPF (lighter weight, no VM overhead). The right choice depends on your trust model: VMs for zero-trust multi-tenant, LSM-BPF for trusted-tenant performance.

## Related pages

- [Kubernetes Agent Sandbox](kubernetes-agent-sandbox.md) — the SIG Apps Sandbox CRD, templates, claims and warm pools.
- [gVisor for AI agent isolation](gvisor-for-ai-agent-isolation.md) — the user-space kernel behind Agent Sandbox: how it works and when to choose it.
- [Kata Containers for AI agents](kata-containers-for-ai-agents.md) — VM-per-sandbox isolation, Kata 4.0 features, and when to choose it over gVisor.
- [Firecracker microVMs for agent sandboxes](firecracker-microvms-for-agent-sandboxes.md) — Firecracker's minimal VMM for per-sandbox kernels, via Kata or Agent Sandbox, and when to choose it.
