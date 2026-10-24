---
title: Cilium
summary: How the graduated CNCF project Cilium uses eBPF for Kubernetes networking, identity-based network policy, multi-cluster connectivity and observability, and when to choose it over kube-proxy/iptables setups.
sources:
  - {video: "bIRwSIwNHC0", t: 0, speaker: "Martynas Pumputis (Cilium)", year: "2019"}
  - {video: "99jUcLt3rSk", t: 1924, speaker: "Daniel Borkmann (Cilium)", year: "2020"}
  - {video: "yikVhGM2ye8", t: 480, speaker: "Raymond de Jong (Isovalent)", year: "2023"}
  - {video: "fJiuqRY5Oi4", t: 49, speaker: "Liz Rice (Isovalent)", year: "2023"}
  - {video: "T_EDE6DDqYc", t: 0, speaker: "Liz Rice (Isovalent)", year: "2025"}
  - {video: "xJ_Jiv7y6N0", t: 439, speaker: "Ahmed (New York Times), Joe (Ascend)", year: "2024"}
  - {video: "2KlVTx611bk", t: 44, speaker: "Moh Ahmed & Raymond Maika (Samsung Ads)", year: "2024"}
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

- **Seznam (Czech search, email and media company)**: replaced F5 hardware load balancers and IPVS (plus Calico for network security) with Cilium's kube-proxy replacement and Maglev-based load balancing, across three data centers, 10,000 bare-metal hosts and Kubernetes on OpenStack; reported figures include 1 million HTTP requests/second and a 100+ cluster mesh, with higher performance, lower capital and operating costs and deeper network visibility [case study](https://www.cncf.io/case-studies/seznam/).
- **PostFinance (Swiss bank)**: with kube-proxy and iptables, getting connectivity for a new pod took several seconds to a minute as clusters grew; moving to Cilium let them remove kube-proxy and use Hubble for observability. The platform is on-premises with 25 shared clusters, 562 nodes and about 4 million customer transactions per day [case study](https://www.cncf.io/case-studies/postfinance/).
- **The New York Times**: runs Cilium on EKS for multi-tenant shared clusters, using Cilium network policies to isolate accounts and tenants, Hubble flows and metrics for security visibility and debugging [▶ 07:19](https://www.youtube.com/watch?v=xJ_Jiv7y6N0&t=439s), ENI mode with secondary VPC IP ranges to avoid IP exhaustion while scaling to thousands of pods, and Cluster Mesh for a flat multi-region network [▶ 08:47](https://www.youtube.com/watch?v=xJ_Jiv7y6N0&t=527s). The speaker says they started this journey about three years earlier. The same project's [adopters list](https://github.com/cilium/cilium/blob/main/USERS.md) describes the New York Times use as multi-region multi-tenant shared clusters on EKS.
- **Samsung Ads**: live-migrated about 20 Rancher-managed clusters (a mix of AWS and bare metal, from tens of nodes to 300-500+) from Calico to Cilium, with more than half running production workloads that carry a significant majority of revenue, so the migration had to keep downtime minimal [▶ 00:44](https://www.youtube.com/watch?v=2KlVTx611bk&t=44s). They tried Multus-based dual-CNI first, which did not work for them because pods could not talk across the two interfaces, and settled on a node-by-node migration using per-node Cilium configuration [▶ 07:13](https://www.youtube.com/watch?v=2KlVTx611bk&t=433s).
- **Ascend (data pipeline platform)**: has used Cilium for about five years, because it deploys into customers' private networks and cloud accounts and must meet PII/PHI compliance and data-path performance needs [▶ 10:16](https://www.youtube.com/watch?v=xJ_Jiv7y6N0&t=616s).
- **Adobe and Datadog (adopters list)**: Adobe's Project Ethos uses Cilium for multi-tenant, multi-cloud clusters with L3/L4/L7 policies; Datadog uses it on self-hosted Kubernetes in AWS for ENI networking, service load balancing, encryption, network policies and Hubble. These are self-reported entries in the project's list [adopters list](https://github.com/cilium/cilium/blob/main/USERS.md).

## Disagreements

None found among the sources. Note the talks span 2019 to 2025, so performance figures from the older talks are dated.

## References

**Talks**

1. [Martynas Pumputis (Cilium), 2019](https://www.youtube.com/watch?v=bIRwSIwNHC0), cited at [00:00](https://www.youtube.com/watch?v=bIRwSIwNHC0&t=0s), [04:19](https://www.youtube.com/watch?v=bIRwSIwNHC0&t=259s)
2. [Liz Rice (Isovalent), 2025](https://www.youtube.com/watch?v=T_EDE6DDqYc), cited at [00:00](https://www.youtube.com/watch?v=T_EDE6DDqYc&t=0s)
3. [Daniel Borkmann (Cilium), 2020](https://www.youtube.com/watch?v=99jUcLt3rSk), cited at [08:01](https://www.youtube.com/watch?v=99jUcLt3rSk&t=481s), [32:04](https://www.youtube.com/watch?v=99jUcLt3rSk&t=1924s), [35:41](https://www.youtube.com/watch?v=99jUcLt3rSk&t=2141s)
4. [Raymond de Jong (Isovalent), 2023](https://www.youtube.com/watch?v=yikVhGM2ye8), cited at [08:00](https://www.youtube.com/watch?v=yikVhGM2ye8&t=480s), [16:48](https://www.youtube.com/watch?v=yikVhGM2ye8&t=1008s)
5. [Liz Rice (Isovalent), 2023](https://www.youtube.com/watch?v=fJiuqRY5Oi4), cited at [00:49](https://www.youtube.com/watch?v=fJiuqRY5Oi4&t=49s), [22:40](https://www.youtube.com/watch?v=fJiuqRY5Oi4&t=1360s)
6. [Ahmed (New York Times), Joe (Ascend), 2024](https://www.youtube.com/watch?v=xJ_Jiv7y6N0), cited at [07:19](https://www.youtube.com/watch?v=xJ_Jiv7y6N0&t=439s), [08:47](https://www.youtube.com/watch?v=xJ_Jiv7y6N0&t=527s), [10:16](https://www.youtube.com/watch?v=xJ_Jiv7y6N0&t=616s)
7. [Moh Ahmed & Raymond Maika (Samsung Ads), 2024](https://www.youtube.com/watch?v=2KlVTx611bk), cited at [00:44](https://www.youtube.com/watch?v=2KlVTx611bk&t=44s), [07:13](https://www.youtube.com/watch?v=2KlVTx611bk&t=433s)

**Documentation, case studies and articles**

1. [docs.cilium.io/en/latest/overview/intro](https://docs.cilium.io/en/latest/overview/intro)
2. [cilium.io/blog](https://cilium.io/blog)
3. [cncf.io/case-studies/seznam](https://www.cncf.io/case-studies/seznam)
4. [cncf.io/case-studies/postfinance](https://www.cncf.io/case-studies/postfinance)
5. [github.com/cilium/cilium/blob/main/USERS.md](https://github.com/cilium/cilium/blob/main/USERS.md)
