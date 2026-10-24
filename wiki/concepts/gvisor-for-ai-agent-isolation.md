---
title: gVisor for AI agent isolation
summary: How gVisor's user-space application kernel sandboxes untrusted, LLM-generated code, and when to pick it over Kata Containers or plain containers.
sources:
  - {video: "c7rsWC8PBHM", t: 271, speaker: "Abdel Sghiouar (Google)", year: "2026"}
  - {video: "ZJH1kYFKjK8", t: 227, speaker: "Abdel Sghiouar (Google)", year: "2026"}
  - {video: "1Ib-rfSzDuM", t: 428, speaker: "Ian Lewis (Google)", year: "2019"}
links: [agent-sandbox-on-cncf, kubernetes-agent-sandbox, kata-containers]
updated: 2026-10-24
clarity_score: 0.0
---

# gVisor for AI agent isolation

> gVisor is the default isolation runtime behind Kubernetes Agent Sandbox. For the wider landscape see [Agent Sandbox on CNCF](agent-sandbox-on-cncf.md); for the Kubernetes API that uses it see [Kubernetes Agent Sandbox](kubernetes-agent-sandbox.md).

## What it is

In plain language: a normal container talks straight to the host's Linux kernel, so one kernel bug can expose every container on the node. gVisor puts a second, much smaller "kernel" written in Go between the container and the real one. The app thinks it is talking to Linux; in fact gVisor answers. The project describes itself as an application kernel that implements a Linux-like interface, written in a memory-safe language (Go) and running in userspace, shipped with an OCI runtime called `runsc` [docs](https://gvisor.dev/docs/).

For agents this matters because they are non-deterministic and may run code you never reviewed. Abdel Sghiouar (Google) notes that agents can generate and execute untrusted code, and that containers alone do not guarantee isolation [▶ 03:47](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=227s). He positions gVisor as the open source isolation technology Agent Sandbox integrates with, though "it's not only gVisor" and Kata Containers or micro VMs also work [▶ 03:47](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=227s).

## How it works

- **Sentry** — the application kernel, one per sandbox. It intercepts and answers the container's system calls. **Gofer** — one per container, provides filesystem access [docs](https://gvisor.dev/docs/).
- Sghiouar's short version: gVisor runs the container "inside a micro kernel with its own gVisor kernel", plus a file system proxy, so there is a layer of isolation between the container and the Linux kernel on the node [▶ 04:31](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=271s).
- Two layers by design. Ian Lewis (Google, KubeCon 2019, older but still the clearest architecture explanation) says an attacker must first break out of the user-space Sentry before sending arbitrary syscalls to the host, and then is limited to a vastly reduced set of syscalls [▶ 18:03](https://www.youtube.com/watch?v=1Ib-rfSzDuM&t=1083s). File access goes through the separate Gofer, so reading or writing an arbitrary file needs a second bug [▶ 23:07](https://www.youtube.com/watch?v=1Ib-rfSzDuM&t=1387s).
- The sandbox itself runs in user mode, so a compromised sandbox does not have root on the host, and Sentry is written in Go, which is memory safe [▶ 24:34](https://www.youtube.com/watch?v=1Ib-rfSzDuM&t=1474s).
- Kubernetes wiring: a RuntimeClass tells containerd to use `runsc` instead of `runc` [▶ 19:28](https://www.youtube.com/watch?v=1Ib-rfSzDuM&t=1168s). In Agent Sandbox the template carries `runtimeClassName: gvisor`, so pods created from it run under gVisor, not regular containerd runtime [▶ 05:14](https://www.youtube.com/watch?v=ZJH1kYFKjK8&t=314s).

## When to use it vs alternatives

| Option | Boundary | Trade-off |
|---|---|---|
| Plain container (runc) | Shared host kernel | Fastest, but one kernel bug away from escape [▶ 08:35](https://www.youtube.com/watch?v=1Ib-rfSzDuM&t=515s) |
| **gVisor** | User-space kernel (process-level, no hardware boundary) | Low fixed overhead and fast start, but lower app compatibility and higher per-syscall cost [docs](https://gvisor.dev/docs/) |
| Kata Containers / Firecracker | Real guest kernel, hardware-enforced via KVM | Stronger boundary; around 5 s cold start including pod scheduling on EKS [docs](https://builder.aws.com/content/3ADDWTtyI2gevtzY9d2vzULAxzS/secure-agent-sandboxes-on-eks) |

Rules of thumb from the sources:

- gVisor suits syscall-light code execution; the docs warn it "may provide poor performance for system call heavy workloads" while VMs face challenges achieving high density [docs](https://gvisor.dev/docs/).
- An AWS Builder Center post puts overhead at 10–30% for I/O-intensive workloads and under 5% end-to-end for agents that mostly wait on LLM responses (the author's figures, not independently verified here) [docs](https://builder.aws.com/content/3ADDWTtyI2gevtzY9d2vzULAxzS/secure-agent-sandboxes-on-eks).
- Only the code-execution step needs the sandbox; a plain agent loop calling APIs can stay in a standard pod [docs](https://builder.aws.com/content/3ADDWTtyI2gevtzY9d2vzULAxzS/secure-agent-sandboxes-on-eks).
- Pair the runtime with warm pools to avoid cold starts. In Sghiouar's demo a used warm-pool pod is replaced by a fresh one after the code runs [▶ 05:15](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=315s).

## Real-world usage

- **Google / GKE** — Google says Agent Sandbox is "foundationally built on gVisor with additional support for Kata Containers" [docs](https://cloud.google.com/blog/products/containers-kubernetes/agentic-ai-on-kubernetes-and-gke).
- **Tencent** — runs millions of gVisor sandboxes daily for Agentic-RL training; after more than 74,000 side-by-side `runsc` vs `runc` comparisons it fixed compatibility issues covering about 1.7% of test cases [docs](https://gvisor.dev/blog/).
- **Multi-agent harnesses** — a gVisor blog post sandboxes OpenClaw, PicoClaw and Hermes Agent each in its own gVisor sandbox [docs](https://gvisor.dev/blog/).
- **Governance** — a 2 October 2026 post states gVisor is being donated to CNCF [docs](https://gvisor.dev/blog/).

## Disagreements

> ⚠ **What kind of thing is gVisor?** Sghiouar calls it a "micro kernel" [▶ 04:31](https://www.youtube.com/watch?v=c7rsWC8PBHM&t=271s), the docs say it is "not a VM in the everyday sense" and not a syscall filter [docs](https://gvisor.dev/docs/), and the AWS post stresses it is process-level, not hardware, isolation [docs](https://builder.aws.com/content/3ADDWTtyI2gevtzY9d2vzULAxzS/secure-agent-sandboxes-on-eks). Treat "micro kernel" as shorthand: the security boundary is software, so for zero-trust multi-tenancy compare it with Kata, as discussed in [Agent Sandbox on CNCF](agent-sandbox-on-cncf.md).
>
> **Age of evidence.** Lewis's architecture talk is from 2019; check current docs for supported syscalls and platforms.
