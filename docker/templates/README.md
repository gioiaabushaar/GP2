# Lab Template Contract

Status: **Draft**. Pending review by Sura Alomari (Backend & AI/RAG) and Ali Alomari (Architecture & DevOps) before any challenge is linked to a template.

Each lab template defines one Docker image with a fixed toolset. A challenge references exactly one template through `lab_template_id`. Each student receives a separate container from that template.

## Required fields

| Field | Type | Description |
|---|---|---|
| `lab_template_id` | string | Unique identifier, lowercase, hyphen-separated. Example: `kali-basics`. |
| `image` | string | Image name and tag. Example: `nexis-kali-basics:v2`. |
| `owner` | string | Team member responsible for the template. |
| `description` | string | One sentence describing the lab's purpose. |
| `tools` | list | Installed tools, each with a reason for inclusion. |
| `user` | string | Non-root UID:GID the container runs as. Must not be `0`. |
| `ports` | list | Exposed ports. Empty list when the network is disabled. |
| `resources.memory` | string | Memory limit, e.g. `128m`. |
| `resources.cpus` | number | CPU limit, e.g. `0.5`. |
| `resources.pids_limit` | integer | Maximum processes per container. |
| `security.network` | string | `none` or a named isolated network. |
| `security.read_only` | boolean | Must be `true` unless a documented writable path is required. |
| `security.cap_drop` | list | Must include `ALL`. |
| `security.no_new_privileges` | boolean | Must be `true`. |
| `ttl_minutes` | integer | Container lifetime. Default `60`. |

## Rules

1. `user` must not be root.
2. `security.cap_drop` must contain `ALL`.
3. Any writable path must be listed explicitly with a reason.
4. A template is not linked to a challenge until its verification tests pass (see below).
5. Changing `image` or `tools` requires a new template version, not an in-place edit.

## Example: `kali-basics`

```yaml
lab_template_id: kali-basics
image: nexis-kali-basics:v2
owner: Hussam Albashir
description: General Linux and network reconnaissance basics.
tools:
  - name: nmap
    reason: Port and service discovery (TCP connect scans only; raw-socket scans disabled)
  - name: curl
    reason: HTTP interaction with challenge targets
  - name: iproute2
    reason: Inspecting interfaces and routes
  - name: iputils-ping
    reason: Reachability checks
  - name: ca-certificates
    reason: TLS trust store for HTTPS tooling
user: "10001:10001"
ports: []
resources:
  memory: 128m
  cpus: 0.5
  pids_limit: 64
security:
  network: none
  read_only: true
  cap_drop: [ALL]
  no_new_privileges: true
ttl_minutes: 60
```

## Verification required before linking

Run each command with all production flags. Each must produce the stated result.

| Check | Command | Expected |
|---|---|---|
| Identity | `id` | `uid=10001(nexis)` |
| Tool works | `nmap --version` | Version printed |
| Network isolation | `ping -c 1 8.8.8.8` | `Network is unreachable` |
| Read-only FS | `touch /etc/test` | `Read-only file system` |
| Raw sockets disabled | `nmap -sS 127.0.0.1` | `Couldn't open a raw socket` |
| No capabilities | `grep Cap /proc/self/status` | All sets `0000000000000000` |

## Open items

- Agree with Sura and Ali on where `lab_template_id` is stored (challenge table column or separate lookup).
- Decide whether `ttl_minutes` is per template or global.
- Pin the base image by digest once the template stabilises.
- Confirm whether `curl` and `iputils-ping` belong in the template or should move to challenge-specific images.