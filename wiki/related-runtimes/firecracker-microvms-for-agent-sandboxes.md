---
title: Firecracker microVMs for agent sandboxes
summary: How Firecracker's minimal Rust VMM gives each AI agent sandbox its own kernel at near-container speed, how it plugs into Kata and Agent Sandbox, and when to pick it over gVisor or plain containers.
sources:
  - {video: "y_vC8oxtbjY", t: 971, speaker: "Prashanth Pai (CodeRabbit)", year: "2026"}
  - {video: "bfmBJ-th2-4", t: 131, speaker: "Lens", year: "2026"}
  - {video: "92MQcV0GSyk", t: 1348, speaker: "Phil Estes (IBM)", year: "2019"}
  - {video: "ZJH1kYFKjK8", t: 227, speaker: "Abdel Sghiouar (Google)", year: "2026"}
  - {video: "lruh-JgbTKM", t: 432, speaker: "Fupan Li & X. Niu (Ant Group)", year: "2026"}
links: [agent-sandbox-on-cncf, kubernetes-agent-sandbox, kata-containers-for-ai-agents, gvisor-for-ai-agent-isolation]
updated: 2026-10-24
clarity_score: 0.0
---

# Firecracker microVMs for agent sandboxes

> Firecracker is a stripped-down virtual machine monitor: it gives every sandbox its own Linux kernel while booting fast enough to feel like a container.

## What it is

When an AI agent runs code an LLM just wrote, that code is effectively untrusted. A regular container shares the host kernel, so one kernel bug can expose the whole node. The Lens explainer puts it bluntly: namespaces and cgroups are "a resource boundary, not a security boundary" [▶ 02:11](https://www.youtube.com/watch?v=bfmBJ-th2-4&t=131s). See [Agent Sandbox on CNCF](../guides/agent-sandbox-on-cncf.md) for the wider problem.

A **microVM** is a real virtual machine with its own kernel, "stripped down to almost nothing", with no emulated legacy hardware [▶ 02:11](https://www.youtube.com/watch?v=bfmBJ-th2-4&t=131s). **Firecracker** is the best-known one. Pai describes Firecracker as the VMM that powers AWS Lambda [▶ 21:19](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1279s). AWS now also sells it directly to agent builders: Lambda MicroVMs, "powered by Firecracker virtualization", give each environment VM-level isolation and can launch from a memory and disk snapshot [docs](https://aws.amazon.com/blogs/compute/running-self-hosted-ai-agent-sandboxes-with-aws-lambda-microvms/).

## How it works

- **KVM plus a user-space VMM.** Pai's layering: KVM in the Linux kernel exposes hardware virtualization, and a VMM such as Firecracker is a user-space process that uses KVM to create and manage VMs. Escaping that boundary needs a hypervisor-level CVE, a class of bug he calls so rare that finding a few would make you "a millionaire" [▶ 21:19](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1279s).
- **A jailer around the VMM.** Estes notes Firecracker adds a seccomp profile that heavily restricts even the VMM's exposure to the host kernel [▶ 22:28](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1348s), plus a jailer that applies cgroup and seccomp restrictions [▶ 26:50](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1610s).
- **Small and fast.** The Lens explainer cites boot times around 125 milliseconds and a few megabytes of memory overhead per instance [▶ 02:11](https://www.youtube.com/watch?v=bfmBJ-th2-4&t=131s). The Agent Sandbox Firecracker example reports the same roughly 125 ms boot [docs](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/firecracker-sandbox/). Treat both as vendor-style figures, not benchmarks of your hardware.
- **Snapshots.** Lambda MicroVMs boot from a pre-captured snapshot, skipping application initialization [docs](https://aws.amazon.com/blogs/compute/running-self-hosted-ai-agent-sandboxes-with-aws-lambda-microvms/). Kata 4.0 added a template-boot feature that supports Cloud Hypervisor and Firecracker, because agent workloads must boot very quickly [▶ 07:12](https://www.youtube.com/watch?v=lruh-JgbTKM&t=432s).

## Running it on Kubernetes

Firecracker does not speak Kubernetes itself. Two common routes:

1. **Via Kata Containers.** Pai notes Kata lets each pod run its own lightweight VM, and you choose the VMM: Firecracker, Cloud Hypervisor or QEMU [▶ 24:12](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1452s). Estes noted Kata added Firecracker support as a backend back in 2018 [▶ 23:57](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1437s). More in [Kata Containers for AI agents](kata-containers-for-ai-agents.md).
2. **Via Agent Sandbox.** Sghiouar says the Sandbox is "just a pod" in a sandboxing technology; gVisor is the default, but it can use Kata or microVMs such as Firecracker [▶ 03:47](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=227s). The upstream example runs a Sandbox on the `kata-fc` RuntimeClass with a SandboxTemplate and a SandboxWarmPool holding 2 warm microVMs [docs](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/firecracker-sandbox/). See [Kubernetes Agent Sandbox](../projects/kubernetes/agent-sandbox.md).

**Practical constraints** from the example docs [docs](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/firecracker-sandbox/):

- Nodes need KVM (`/dev/kvm`); macOS and Windows hosts cannot run `kata-fc`.
- Firecracker does not support overlayfs or virtio-fs for the rootfs, so containerd needs the devmapper snapshotter or similar.

Estes made a related point in 2019: volume mounts did not work with Firecracker then, because it was built narrowly for the Lambda use case [▶ 27:33](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1653s). Check current behaviour before relying on that.

## When to use it vs alternatives

| Option | Boundary | Pick it when |
|---|---|---|
| Plain container | Shared host kernel | Code you wrote and reviewed. The Lens talk keeps containers for trusted parts like the orchestrator and agent runtime [▶ 02:11](https://www.youtube.com/watch?v=bfmBJ-th2-4&t=131s). |
| [gVisor](gvisor-for-ai-agent-isolation.md) | User-space kernel | You have no KVM, or want the Agent Sandbox default. |
| [Kata](kata-containers-for-ai-agents.md) + QEMU/Cloud Hypervisor | Guest kernel | You need general-purpose container behaviour. |
| Firecracker (direct or `kata-fc`) | Guest kernel, minimal VMM | Short-lived, bursty, untrusted code at high density. |

Estes's guidance holds: the choice depends on your threat model and use case [▶ 33:22](https://www.youtube.com/watch?v=92MQcV0GSyk&t=2002s).

## Real-world usage

- **CodeRabbit** describes a coding-agent architecture in which the actual coding work happens in "a lightweight virtual machine that's powered by Firecracker", fronted by a firewall and a credentials broker [▶ 16:11](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=971s).
- **Sandbox providers.** Pai lists Vercel and fly.io as using Firecracker VMs, Modal using gVisor, and Docker sandboxes using their own microVM [▶ 30:47](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1847s). Wenjie Bao mentions E2B running on Firecracker [▶ 03:34](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=214s).
- **AWS** offers Firecracker-backed Lambda MicroVMs for self-hosted agent sandboxes, each running for up to 8 hours and able to be launched, suspended, resumed and terminated programmatically [docs](https://aws.amazon.com/blogs/compute/running-self-hosted-ai-agent-sandboxes-with-aws-lambda-microvms/).

Pai's practical advice: assume exfiltration is always possible from the sandbox, so tokenize secrets or proxy them, and for most use cases use a ready-made sandbox rather than building your own [▶ 30:47](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1847s).

## Disagreements

> ⚠ The sources disagree on how much VM-grade isolation is worth. The Lens explainer says microVMs win for agent execution "and it's not even close" [▶ 02:11](https://www.youtube.com/watch?v=bfmBJ-th2-4&t=131s). Sghiouar, speaking for Agent Sandbox, keeps gVisor as the default and treats Firecracker as one pluggable option [▶ 03:47](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=227s). Wang's team, by contrast, chose Kata with a full guest kernel and worked on boot cost ([Agent Sandbox on CNCF](../guides/agent-sandbox-on-cncf.md)). The Lens video is also a vendor pitch for its own product, so weigh it accordingly.

## Related pages

- [Agent Sandbox on CNCF](../guides/agent-sandbox-on-cncf.md)
- [Kubernetes Agent Sandbox](../projects/kubernetes/agent-sandbox.md)
- [Kata Containers for AI agents](kata-containers-for-ai-agents.md)
- [gVisor for AI agent isolation](gvisor-for-ai-agent-isolation.md)

## References

**Talks**

1. [Lens, 2026](https://www.youtube.com/watch?v=bfmBJ-th2-4), cited at [02:11](https://www.youtube.com/watch?v=bfmBJ-th2-4&t=131s)
2. [Prashanth Pai (CodeRabbit), 2026](https://www.youtube.com/watch?v=y_vC8oxtbjY), cited at [16:11](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=971s), [21:19](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1279s), [24:12](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1452s), [30:47](https://www.youtube.com/watch?v=y_vC8oxtbjY&t=1847s)
3. [Phil Estes (IBM), 2019](https://www.youtube.com/watch?v=92MQcV0GSyk), cited at [22:28](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1348s), [23:57](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1437s), [26:50](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1610s), [27:33](https://www.youtube.com/watch?v=92MQcV0GSyk&t=1653s), [33:22](https://www.youtube.com/watch?v=92MQcV0GSyk&t=2002s)
4. [Fupan Li & X. Niu (Ant Group), 2026](https://www.youtube.com/watch?v=lruh-JgbTKM), cited at [07:12](https://www.youtube.com/watch?v=lruh-JgbTKM&t=432s)
5. [Abdel Sghiouar (Google), 2026](https://www.youtube.com/watch?v=ZJH1kYFKjK8), cited at [03:47](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=227s)
6. [YouTube video Qcuzt2YkdMs](https://www.youtube.com/watch?v=Qcuzt2YkdMs), cited at [03:34](https://www.youtube.com/watch?v=Qcuzt2YkdMs&t=214s)

**Documentation, case studies and articles**

1. [aws.amazon.com/blogs/compute/running-self-hosted-ai-agent-sandboxes-with-aws-lambda-microvms](https://aws.amazon.com/blogs/compute/running-self-hosted-ai-agent-sandboxes-with-aws-lambda-microvms)
2. [agent-sandbox.sigs.k8s.io/docs/use-cases/examples/firecracker-sandbox](https://agent-sandbox.sigs.k8s.io/docs/use-cases/examples/firecracker-sandbox)
