---
title: Kubernetes Agent Sandbox (kubernetes-sigs/agent-sandbox)
summary: The SIG Apps project that adds a Sandbox CRD, templates, claims and warm pools to Kubernetes for running isolated, stateful AI agent workloads.
sources:
  - {video: "c7rsWC8PBHM", t: 227, speaker: "Abdel Sghiouar (Google)", year: "2026"}
  - {video: "ZJH1kYFKjK8", t: 227, speaker: "Abdel Sghiouar (Google)", year: "2026"}
  - {video: "aFX_6HL_i80", t: 1618, speaker: "Xu Wang & Yu Hu", year: "2026"}
links: [agent-sandbox-on-cncf, agent-substrate, kata-containers, kagent]
updated: 2026-10-24
clarity_score: 0.0
---

# Kubernetes Agent Sandbox

> The upstream Kubernetes project for giving each AI agent its own isolated, long-lived, single-pod environment. For the wider CNCF landscape see [Agent Sandbox on CNCF](agent-sandbox-on-cncf.md).

## What it is

Agent Sandbox (`kubernetes-sigs/agent-sandbox`) is a Custom Resource Definition and controller, developed under SIG Apps, for managing isolated, stateful, singleton workloads such as AI agent runtimes and reinforcement learning [docs](https://github.com/kubernetes-sigs/agent-sandbox). Put simply: a Sandbox is a pod with a stable name, optional persistent disk, and a managed lifecycle, run on a hardened runtime so untrusted, LLM-generated code can't touch the rest of the cluster.

Abdel Sghiouar (Google) describes it in a talk as "just a pod that actually runs within some sort of sandboxing technology" [▶ 03:47](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=227s). The Kubernetes blog frames the gap it fills: you could approximate it with a StatefulSet of size 1, a headless Service and a PVC per agent, but managing that at scale becomes "an operational nightmare" [docs](https://kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/).

## Why agents need it

Sghiouar's argument: agents are non-deterministic, can generate and execute untrusted code, and may be pointed at tools you cannot fully control. He cites the case of Replit's agent that deleted a database because it had unlimited access [▶ 03:47](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=227s). Removing the code-execution ability would defeat the purpose of having an agent, so the code must run somewhere isolated instead.

## How it works

Core object and extensions, per the project README [docs](https://github.com/kubernetes-sigs/agent-sandbox):

| Resource | Role |
|---|---|
| `Sandbox` | Core CRD: one stateful pod with stable identity, persistent storage, lifecycle (creation, scheduled deletion, pause/resume) |
| `SandboxTemplate` | Reusable blueprint for sandboxes |
| `SandboxClaim` | Request to get a sandbox, e.g. from a warm pool |
| `SandboxWarmPool` | Pool of pre-warmed sandboxes for fast allocation |

- **Isolation is delegated.** Agent Sandbox is an orchestrator; it relies on sandbox runtimes such as gVisor or Kata Containers via `RuntimeClass` [docs](https://github.com/kubernetes-sigs/agent-sandbox). In the talk, gVisor is the default "because this was built by Google", with Kata Containers or Firecracker-style microVMs also possible [▶ 03:47](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=227s).
- **Templates are classes, sandboxes are instances.** The runtime class (e.g. gVisor) in the template is what makes pods created from it run sandboxed instead of with the regular runtime [▶ 05:14](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=314s).
- **Warm pools kill cold starts.** The Kubernetes blog notes a new pod adds about a second of overhead, and SandboxWarmPool maintains pre-provisioned pods so a SandboxClaim is handed a ready environment [docs](https://kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/). The Google Open Source blog says this reduces cold-start latency to under one second [docs](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html).
- **Request flow.** The SDK client calls a router (a proxy in the cluster); it assigns a warm-pool pod if one exists, otherwise spins up a new one, and the pool replaces the used pod [▶ 11:06](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=666s). Spinning up a new one "can take a couple of seconds" while assigning a warm one is faster [▶ 11:06](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=666s).
- **Policies in templates.** Templates can carry network policies, e.g. blocking all external traffic [▶ 10:23](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=623s). The docs ship a hardened example with gVisor and DNS-only egress [docs](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/warmpool-quickstart/).
- **Shutdown time and SDK.** An absolute shutdown time automates cleanup, and a Python SDK wraps the CRDs [docs](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html).

### Demo: why it matters

Sghiouar prompts an agent to print its environment variables. With the sandbox, the output comes from an ephemeral pod that has since been deleted, not the agent's own runtime [▶ 08:55](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=535s).

## When to use it vs alternatives

- **Use it** when agents execute untrusted code, need a persistent identity or scratch disk, or sit idle for long periods. The blog says it supports scaling idle environments to zero and resuming where they left off [docs](https://kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/).
- **Local dev tools** such as Gemini CLI or Codex have their own local sandboxing, not gVisor [▶ 12:35](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=755s).
- **Higher density:** Lin Sun (Solo.io) argues sandboxing is necessary but not sufficient; [Agent Substrate](agent-sandbox-on-cncf.md) lets agents run in short bursts on shared workers and suspend when idle, rather than one always-on pod each [docs](https://www.cncf.io/blog/2026/07/07/why-sandboxing-your-agent-is-not-enough/).
- **Self-hosted VM stack:** Japan AI / Ant Group combined the agent-sandbox CRD (v0.5.3), Kata on EKS and an image service, and measured about 1.4 seconds for a warm start [▶ 26:58](https://www.youtube.com/watch?v=aFX_6HL_i80&t=1618s). See the hub page for the Kata-based architecture.

## Real-world usage

Sghiouar says Lovable, a Swedish vibe-coding platform, uses it in production: each user writing an application gets a pod from a warm pool [▶ 11:06](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=666s), protecting Lovable's cluster from the customers' agents [▶ 12:35](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=755s). GKE offers a managed add-on based on the open-source controller [docs](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/machine-learning/agent-sandbox).

## Disagreements

> ⚠ The Kubernetes blog describes the project as "currently in development under SIG Apps" [docs](https://kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/), while the talks present it as production-used by Lovable [▶ 11:06](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=666s). Treat APIs as fast-moving. Also, the default gVisor (user-space kernel) differs from the VM-per-sandbox view in the hub page; the project is runtime-agnostic, so the choice is yours.

## Sources

Talks: Sghiouar at PlatformCon 2026 (`c7rsWC8PBHM`) and Jfokus 2026 (`ZJH1kYFKjK8`); Xu Wang & Yu Hu at KubeCon Japan 2026 (`aFX_6HL_i80`). Docs: project README, Kubernetes blog (Mar 2026), Google Open Source blog (Nov 2025), CNCF blog (Jul 2026), GKE docs.
