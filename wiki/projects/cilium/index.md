---
title: Cilium
summary: How the graduated CNCF project Cilium uses eBPF for Kubernetes networking, identity-based network policy, multi-cluster connectivity and observability, and when to choose it over kube-proxy/iptables setups.
sources:
  - {video: "bIRwSIwNHC0", t: 0, speaker: "Martynas Pumputis (Cilium)", year: "2019"}
  - {video: "99jUcLt3rSk", t: 1924, speaker: "Daniel Borkmann (Cilium)", year: "2020"}
  - {video: "yikVhGM2ye8", t: 480, speaker: "Raymond de Jong (Isovalent)", year: "2023"}
  - {video: "fJiuqRY5Oi4", t: 49, speaker: "Liz Rice (Isovalent)", year: "2023"}
  - {video: "T_EDE6DDqYc", t: 0, speaker: "Liz Rice (Isovalent)", year: "2025"}
links: [agent-sandbox-on-cncf, gvisor-for-ai-agent-isolation, kata-containers-for-ai-agents, kubernetes-agent-sandbox]
updated: 2026-10-24
clarity_score: 0.0
---

# Cilium

> A graduated CNCF project that uses eBPF inside the Linux kernel to connect, secure and observe Kubernetes workloads.

## What it is

Cilium is open source software for transparently securing network connectivity between application services running on platforms like Docker and Kubernetes; its foundation is the Linux kernel technology eBPF [docs](https://docs.cilium.io/en/latest/overview/intro/). In plain terms: it is a Kubernetes networking layer (a CNI plugin plus a network security plugin) [▶ 00:00](https://www.youtube.com/watch?v=bIRwSIwNHC0&t=0s) that does its packet handling in small verified programs in the kernel instead of long chains of firewall rules.

Cilium was announced as the first graduated CNI by the CNCF in October 2023 [docs](https://cilium.io/blog/). By 2025 it was described as the top choice in the CNCF technology radar, especially for multicluster environments, with Hubble for network observability and Tetragon for runtime security [▶ 00:00](https://www.youtube.com/watch?v=T_EDE6DDqYc&t=0s).

## How it works

**eBPF as the engine.** Borkmann stresses eBPF programs cannot crash the kernel, are as fast as a kernel module, and come with stable API guarantees [▶ 08:01](https://www.youtube.com/watch?v=99jUcLt3rSk&t=481s).

**Replacing kube-proxy and iptables.** Pumputis explains why: reliability issues in netfilter/iptables, such as kube-dns taking five seconds to reply to DNS requests [▶ 04:19](https://www.youtube.com/watch?v=bIRwSIwNHC0&t=259s). Cilium's service handling has two parts: BPF programs at the socket layer, and BPF programs at the XDP and tc layers [▶ 32:04](https://www.youtube.com/watch?v=99jUcLt3rSk&t=1924s). In Borkmann's benchmark, at the tc layer Cilium handled around 3.5 million packets per second, while kube-proxy had more overhead because netfilter sits later in the stack [▶ 35:41](https://www.youtube.com/watch?v=99jUcLt3rSk&t=2141s). (These are numbers from a 2020 test setup, not a current guarantee.)

**Identity-based policy.** Cilium policies select workloads by label-derived identity rather than by IP, and the same identities secure and observe traffic across clusters; a policy can allow access from one specific cluster and drop traffic from another [▶ 16:48](https://www.youtube.com/watch?v=yikVhGM2ye8&t=1008s).

**Cluster Mesh and encryption.** Cilium Mesh builds on basic Kubernetes concepts to connect workloads in the same cluster, other clusters, or outside Kubernetes [▶ 00:49](https://www.youtube.com/watch?v=fJiuqRY5Oi4&t=49s). Workloads can be mutually authenticated and the resulting certificates injected into the kernel to encrypt traffic, in-cluster or out [▶ 22:40](https://www.youtube.com/watch?v=fJiuqRY5Oi4&t=1360s).

## Adopting network policy with Hubble

De Jong recommends starting with default per-namespace policies while using Hubble to observe egress and ingress flows, then moving to fine-grained policies, with global policies as guardrails, beginning with the most sensitive namespaces [▶ 08:00](https://www.youtube.com/watch?v=yikVhGM2ye8&t=480s).

## When to use it vs alternatives

- **vs kube-proxy + iptables:** pick Cilium when rule-chain debugging and performance at scale hurt; Cilium can replace kube-proxy entirely [▶ 32:04](https://www.youtube.com/watch?v=99jUcLt3rSk&t=1924s).
- **Multi-cloud / multi-cluster:** one consistent networking layer across clouds is the draw [▶ 00:00](https://www.youtube.com/watch?v=T_EDE6DDqYc&t=0s).
- **For sandboxed AI agents:** Cilium does not isolate kernels. Containers still share a kernel, which is why [Agent Sandbox on CNCF](../../guides/agent-sandbox-on-cncf.md) pairs runtimes such as [gVisor](../../related-runtimes/gvisor-for-ai-agent-isolation.md) or [Kata Containers](../../related-runtimes/kata-containers-for-ai-agents.md) with network controls. Cilium's identity-aware network policy is the natural layer for limiting what a sandbox may reach (egress allow-lists); this is an inference from the sources above, not something a cited talk states.

## Real-world usage

Borkmann notes many large-scale Cilium users run it in production [▶ 31:21](https://www.youtube.com/watch?v=99jUcLt3rSk&t=1881s). Pumputis says Cilium's maintainers work with some of the largest and most sophisticated Kubernetes users [▶ 00:00](https://www.youtube.com/watch?v=bIRwSIwNHC0&t=0s).

## Disagreements

None found among the sources. Note the talks span 2019 to 2025, so performance figures from the older talks are dated.
