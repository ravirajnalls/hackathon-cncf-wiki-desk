---
title: Kata Containers for AI agents
summary: How Kata Containers gives each AI agent sandbox its own lightweight VM and guest kernel, what Kata 4.0 changes, and when to pick it over gVisor or plain containers.
sources:
  - {video: "lruh-JgbTKM", t: 175, speaker: "Fupan Li & X. Niu (Ant Group)", year: "2026"}
  - {video: "Qcuzt2YkdMs", t: 520, speaker: "Wenjie Bao", year: "2026"}
  - {video: "aFX_6HL_i80", t: 487, speaker: "Xu Wang (Ant Group) & Yu Hu (JAPAN AI)", year: "2026"}
  - {video: "bdoF5hQojaA", t: 130, speaker: "OpenInfra Foundation (Kata community)", year: "2025"}
links: [agent-sandbox-on-cncf, kubernetes-agent-sandbox, gvisor-for-ai-agent-isolation, kata-containers]
updated: 2026-10-24
clarity_score: 0.0
---

# Kata Containers for AI agents

> Kata is the "real guest kernel" option in the agent-sandbox landscape. For the wider picture see [Agent Sandbox on CNCF](../guides/agent-sandbox-on-cncf.md); for the Kubernetes API that can launch Kata pods see [Kubernetes Agent Sandbox](../projects/kubernetes/agent-sandbox.md).

## What it is

In plain language: a normal container shares the host's Linux kernel, so one kernel bug can let agent-written code reach every other container on the node. Kata Containers instead starts a small virtual machine for each pod and runs the container inside it, so the container looks and behaves like a normal one but sits behind a hardware virtualization boundary. The project describes itself as lightweight VMs that "feel and perform like containers" with hardware virtualization as a second layer of defense, stewarded by the Open Infrastructure Foundation [docs](https://katacontainers.io/).

The Kata 4.0 speakers put it the same way: shared-kernel containers can be broken out of via a CVE, whereas Kata boots a VM and uses the kata agent to run the container inside, so a workload that breaks out of the container still cannot leave the VM [▶ 02:55](https://www.youtube.com/watch?v=lruh-JgbTKM&t=175s).

Why it matters for agents: Wenjie Bao argues LLM output is untrusted code you cannot review or predict, so it "deserve[s] a hardware boundary, not a namespace" [▶ 08:40](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=520s).

## How it works

- **One pod, one VM.** Xu Wang: each sandbox gets its own guest kernel, so exploiting the kernel only hits that guest, not other tenants [▶ 08:07](https://www.youtube.com/watch?v=aFX_6HL_i80&t=487s). Kata keeps the standard workflow: same images, same Kubernetes, just a different runtime class [▶ 08:07](https://www.youtube.com/watch?v=aFX_6HL_i80&t=487s).
- **Kata 4.0 runtime.** The agent and shim were rewritten in Rust, and with the hypervisor folded in, components collapse into one process [▶ 04:24](https://www.youtube.com/watch?v=lruh-JgbTKM&t=264s). Xu Wang adds that this simplifies management and speeds things up [▶ 13:13](https://www.youtube.com/watch?v=aFX_6HL_i80&t=793s).
- **Multiple hypervisors.** QEMU, Cloud Hypervisor and Dragonball (contributed by Alibaba Cloud and Ant Group) are supported, and others can be plugged in [▶ 05:06](https://www.youtube.com/watch?v=lruh-JgbTKM&t=306s). The Kata site lists QEMU, Cloud-Hypervisor and Firecracker, plus containerd integration [docs](https://katacontainers.io/).
- **Template boot.** A traditional VM boot takes too long for agents, so 4.0 supports booting from a template (Cloud Hypervisor, Firecracker, Dragonball); the speaker claims about 20 ms versus a cold boot [▶ 07:56](https://www.youtube.com/watch?v=lruh-JgbTKM&t=476s).
- **Checkpoint/restore.** Kata VM memory can be dumped to the host and restored on another node; the Kubernetes support is a patch submitted to the community and still under review [▶ 08:39](https://www.youtube.com/watch?v=lruh-JgbTKM&t=519s).
- **PVM.** Xu Wang's team also uses a page-table-based KVM driver so VMs run on cloud instances without nested virtualization, which they say they tested in Ant Group production [▶ 14:41](https://www.youtube.com/watch?v=aFX_6HL_i80&t=881s).
- **Confidential computing.** Kata supports Intel TDX and AMD SEV-SNP [▶ 06:30](https://www.youtube.com/watch?v=lruh-JgbTKM&t=390s), and the Kata/Confidential Containers stack is pitched as a "lift and shift" path for existing containers into a confidential context without code changes [▶ 02:54](https://www.youtube.com/watch?v=bdoF5hQojaA&t=174s), selected per pod via RuntimeClass [▶ 03:43](https://www.youtube.com/watch?v=bdoF5hQojaA&t=223s).

## When to use it vs alternatives

| Option | Boundary | Trade-off |
|---|---|---|
| Plain container (runc) | Shared host kernel | Fastest, but a kernel exploit reaches the host and other containers [▶ 08:40](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=520s) |
| [gVisor](gvisor-for-ai-agent-isolation.md) | User-space kernel, software boundary | Low overhead, weaker app compatibility |
| **Kata Containers** | Guest kernel behind a hypervisor | Stronger boundary; cost is one VM per sandbox [▶ 09:24](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=564s) |
| Confidential Containers (Kata + TEE) | VM plus encrypted memory | For when you do not trust the infrastructure either |

Guidance from the sources:

- Choose Kata for zero-trust, multi-tenant agent code execution where a hardware-enforced boundary is the requirement [▶ 08:07](https://www.youtube.com/watch?v=aFX_6HL_i80&t=487s).
- Sandboxes such as Firecracker, gVisor and Kata reduce the blast radius, but you still trust the host and infrastructure; if you do not, add confidential computing [▶ 02:10](https://www.youtube.com/watch?v=bdoF5hQojaA&t=130s).
- Use warm pools to hide VM boot cost (see below). In Kubernetes, Kata is reached through [Kubernetes Agent Sandbox](../projects/kubernetes/agent-sandbox.md) templates and runtime classes.

## Real-world usage

- **Japan AI / Ant Group** — Agent Sandbox CRD plus Kata on EKS, containerd, Dragonfly and Nydus image distribution; they measured about 1.4 seconds for a warm-start container, said it still needs long-term evaluation, and had not tested PVM in that environment [▶ 26:58](https://www.youtube.com/watch?v=aFX_6HL_i80&t=1618s).
- **OpenStack Zun + Kata** — every sandbox is a Kata container with its own guest kernel, scheduled by Zun [▶ 06:29](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=389s). Measured on a three-node cluster with a 500 MB image: cold create P50 5 s, warm-pool hit 0.1 s, about 5% execution overhead versus bare metal, 85% warm-pool hit rate [▶ 23:57](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=1437s); cold P99 8.9 s, warm P99 0.2 s [▶ 24:40](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=1480s). These are the speaker's own production numbers.
- **Network design around Kata** — separate manager and sandbox networks that are never routed together, SNAT-only egress and no inbound path [▶ 10:09](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=609s); a lesson learned was that one agent reached an internal metadata service, fixed by default-deny security groups [▶ 26:07](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=1567s).
- **Multi-tenant Kubernetes clusters** — a KubeCon China 2026 session by Pengfei Ni describes Kata VM isolation, per-agent OIDC identity, NetworkPolicy blocking IMDS and admission policies for hundreds of agents; no transcript was available, so this rests on the session abstract [docs](https://confpad.io/conferences/kubecon-cloudnativecon-openinfra-summit-pytorch-conference-china-2026/what-we-learned-securing-ai-agents-at-scale-on-multi-tenant-kubernetes-clusters).
- **Google** — GKE's Agent Sandbox is described as built on gVisor "with additional support for Kata Containers" [docs](https://cloud.google.com/blog/products/containers-kubernetes/agentic-ai-on-kubernetes-and-gke).

## Disagreements

> ⚠ **How fast is Kata start-up?** The Kata 4.0 speaker claims about 20 ms template boot [▶ 07:56](https://www.youtube.com/watch?v=lruh-JgbTKM&t=476s), but the live demo showed VM restore of 6 ms and 20 ms with end-to-end launches of 221 ms (block device) and 160 ms (virtio-fs) [▶ 15:59](https://www.youtube.com/watch?v=lruh-JgbTKM&t=959s) [▶ 16:42](https://www.youtube.com/watch?v=lruh-JgbTKM&t=1002s). Meanwhile the Zun deployment sees 5 s cold create and Japan AI 1.4 s warm start, because they include scheduling, images and pod machinery. Compare like with like: VM restore, container launch and full pod creation are different measurements.
>
> **Is the VM cost acceptable?** Bao calls the per-sandbox VM cost small enough for ephemeral sandboxes [▶ 09:24](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=564s), while the earlier Japan AI talk concedes VMs cost more start-up time and memory that "should be solved by the technology" (see [Agent Sandbox on CNCF](../guides/agent-sandbox-on-cncf.md)).
>
> **Maturity caveats.** Kata 4.0 had been out only weeks at the time of the talks [▶ 13:13](https://www.youtube.com/watch?v=aFX_6HL_i80&t=793s), and Kubernetes checkpoint/restore for Kata was still under review [▶ 08:39](https://www.youtube.com/watch?v=lruh-JgbTKM&t=519s).
