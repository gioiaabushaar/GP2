# NEXIS GP2 — Web Security Lab / Reverse Proxy Test Results

**Repository destination:** `docker/web-security/TEST_RESULTS.md`

**Test date:** 2026-11-21

**Environment:** Windows PowerShell, Docker Desktop (Linux containers), one host computer

**Branch during tests:** `feature/web-security-lab`

**Scope:** Two simulated student sessions (A and B), each with a separate web target, private session network, and dedicated reverse proxy.

**Evidence:** User-provided PowerShell output, `docker inspect` results, Docker logs, and runtime checks. Results describe the tested local deployment, not an independent production security assessment.

## 1. Tested topology

| Session | Web target | Private session network | Reverse proxy | Edge network | Host-facing endpoint | Configured upstream |
|---|---|---|---|---|---|---|
| A | `nexis-web-session-a` | `nexis-session-a` | `nexis-proxy-a2` | `nexis-edge-a` | `127.0.0.1:8083` | `nexis-web-session-a:8080` |
| B | `nexis-web-session-b` | `nexis-session-b` | `nexis-proxy-b2` | `nexis-edge-b` | `127.0.0.1:8084` | `nexis-web-session-b:8080` |

The proxies were created from the same image, `nexis-web-proxy:v2`, using the required startup environment variable `NEXIS_UPSTREAM_HOST`. The proxy startup logs showed the correct upstream for each session. The web targets used `nexis-web-security:v1`.

At the time of testing, `nexis-web-session-a` had IP `172.19.0.2` and `nexis-web-session-b` had IP `172.21.0.2`. These are ephemeral Docker addresses, not stable application configuration.

**Network checks:** `docker network inspect nexis-session-b --format '{{.Internal}}'` returned `true`. Inspection showed the B proxy connected to `nexis-edge-b` and `nexis-session-b`, while the B target was connected only to `nexis-session-b`. The `Internal` property of `nexis-session-a` was not captured and remains unverified.

## 2. Functional and isolation test results

| ID | Test | Observed evidence | Status |
|---|---|---|---|
| **T01** | Session B: host → Proxy B2 → Web B via `GET /training-hint` | `curl.exe -i http://127.0.0.1:8084/training-hint` returned `HTTP/1.0 200 OK` and `NEXIS{web_recon_basics}` | **PASS — HTTP** |
| **T02** | Proxy A2 → Web B by container DNS name | Connecting to `nexis-web-session-b:8080` returned `socket.gaierror: [Errno -2] Name does not resolve` | **PASS — DNS separation** |
| **T03** | Proxy B2 → Web A by container DNS name | Connecting to `nexis-web-session-a:8080` returned `socket.gaierror: [Errno -2] Name does not resolve` | **PASS — DNS separation** |
| **T04** | Proxy A2 → Web B by direct IP | Connecting to `172.21.0.2:8080` with a 3-second timeout returned `TimeoutError: timed out` | **PASS — cross-session TCP connection not established** |
| **T05** | Proxy B2 → Web A by direct IP | Connecting to `172.19.0.2:8080` with a 3-second timeout returned `TimeoutError: timed out` | **PASS — cross-session TCP connection not established** |
| **T06** | Proxy A2 → Web A, TCP connectivity on port 8080 | `socket.create_connection` to `nexis-web-session-a:8080` succeeded and printed `OK` | **PASS — TCP connectivity only; no HTTP request was made** |
| **T07** | Session A: host → recreated Proxy A2 → Web A via `GET /training-hint` | `curl.exe -i http://127.0.0.1:8083/training-hint` returned `HTTP/1.0 200 OK` and `NEXIS{web_recon_basics}` | **PASS — HTTP** |

**T06 interpretation:** The printed `OK` came from a TCP connection test only. It did not issue an HTTP request and must not be cited as evidence of HTTP path behaviour. T07 separately establishes successful HTTP access through the recreated A2 proxy.

**Earlier v1-only HTTP checks:** The previous proxy on `127.0.0.1:8081` returned `200 OK` for `GET /`, `200 OK` for `GET /training-hint`, `404 Not Found` for `GET /health`, and `405 Method Not Allowed` for `POST /`. These results relate to v1, not to a fresh method/path-filtering test of the final v2 proxies.

### 2.1 Path handling tests (v2 proxy A2)

The following local HTTP requests used `curl.exe -i --path-as-is` against `127.0.0.1:8083` to preserve the client-supplied path. The observed statuses are supported by the response output and `docker logs nexis-proxy-a2`.

| ID | Request | Observed status | Assessment |
|---|---|---|---|
| T08 | `GET //training-hint` | `200 OK` | Path normalised by Python `BaseHTTPRequestHandler.parse_request()` to `/training-hint` before the proxy's allowlist check. Observed library behaviour, **not an independent access-control guarantee**. |
| T09 | `GET /./training-hint` | `404 Not Found` | Rejected by the proxy allowlist. |
| T10 | `GET /%68ealth` | `404 Not Found` | Rejected by the proxy allowlist; the percent-encoded spelling did not match an allowed path. |
| T11 | `GET //health` | `404 Not Found` | Rejected by the proxy allowlist after Python's double-slash normalisation. |
| T12 | `GET /health` | `404 Not Found` | Rejected by the proxy allowlist. |

**T08 — Path normalisation:** `GET //training-hint` returned `200 OK` through the proxy, while the proxy log retained the original request form (`"GET //training-hint HTTP/1.1"`). The Python standard-library `BaseHTTPRequestHandler.parse_request()` code inspected inside `nexis-proxy-a2` (Python 3.12.16) rewrites paths beginning with `//` to a single leading slash before `do_GET()` is invoked. The inspected standard-library source includes a comment linking this handling to open-redirect prevention and referencing `gh-87389` (as indicated by the code comment in the inspected source; the issue reference was not independently verified). The allowlist therefore received `/training-hint`. This result is library-dependent; it does **not** establish that the proxy independently validates the original raw path.

**Security limitation:** The prototype uses the path representation supplied by Python `http.server`. Future production-grade handling should define and enforce canonical URL-path rules explicitly, reject unsupported representations, and apply authenticated access control at an appropriate gateway.

**Reproduction commands:**

```powershell
curl.exe -i --path-as-is http://127.0.0.1:8083//training-hint
curl.exe -i --path-as-is http://127.0.0.1:8083/./training-hint
curl.exe -i --path-as-is http://127.0.0.1:8083/%68ealth
curl.exe -i --path-as-is http://127.0.0.1:8083//health
curl.exe -i --path-as-is http://127.0.0.1:8083/health
```

### Reproducible commands (Windows PowerShell)

```powershell
# HTTP through each v2 proxy
curl.exe -i http://127.0.0.1:8083/training-hint
curl.exe -i http://127.0.0.1:8084/training-hint

# Cross-session DNS checks (expected: name resolution failure)
docker exec nexis-proxy-a2 python -c "import socket; socket.create_connection(('nexis-web-session-b', 8080), timeout=3)"
docker exec nexis-proxy-b2 python -c "import socket; socket.create_connection(('nexis-web-session-a', 8080), timeout=3)"

# Cross-session direct-IP checks (expected in observed environment: timeout)
docker exec nexis-proxy-a2 python -c "import socket; socket.create_connection(('172.21.0.2', 8080), timeout=3); print('CONNECTED')"
docker exec nexis-proxy-b2 python -c "import socket; socket.create_connection(('172.19.0.2', 8080), timeout=3); print('CONNECTED')"

# Positive control: same-session TCP connectivity (expected: OK)
docker exec nexis-proxy-a2 python -c "import socket; socket.create_connection(('nexis-web-session-a', 8080), timeout=3); print('OK')"
```

The IP addresses in the cross-session commands were observed at test time. Obtain fresh values using `docker inspect` before any later rerun.

## 3. Docker security configuration verification

The following settings were checked using `docker inspect ... --format '{{json .HostConfig}}'`.

| Container | `CapDrop` | `ReadonlyRootfs` | `SecurityOpt` | `Privileged` | Memory limit | CPU limit | `PidsLimit` | Host `PortBindings` |
|---|---|---|---|---|---|---|---|---|
| `nexis-proxy-a2` | `ALL` | `true` | `no-new-privileges:true` | `false` | 64 MiB | 0.25 | 32 | `127.0.0.1:8083` |
| `nexis-web-session-a` | `ALL` | `true` | `no-new-privileges:true` | `false` | 128 MiB | 0.5 | 64 | none |
| `nexis-proxy-b2` | `ALL` | `true` | `no-new-privileges:true` | `false` | 64 MiB | 0.25 | 32 | `127.0.0.1:8084` |
| `nexis-web-session-b` | `ALL` | `true` | `no-new-privileges:true` | `false` | 128 MiB | 0.5 | 64 | none |

**Units:** `Memory` values were 67108864 bytes (64 MiB) for each proxy and 134217728 bytes (128 MiB) for each web target. `NanoCpus` was 250000000 (0.25 CPU) for each proxy and 500000000 (0.5 CPU) for each web target. Each container had `/tmp` mounted as `tmpfs`.

**Swap policy:** `MemorySwap` was 134217728 bytes (128 MiB) for each proxy and 268435456 bytes (256 MiB) for each web target. This allows additional swap within Docker's memory+swap accounting, subject to host support. It is not a claim that swap was used. Setting `--memory-swap` equal to `--memory` would further restrict swap in a future run.

### 3.1 Runtime Linux capabilities

The following commands were run inside each of the four containers:

```powershell
docker exec nexis-proxy-a2 sh -c "grep Cap /proc/self/status"
docker exec nexis-web-session-a sh -c "grep Cap /proc/self/status"
docker exec nexis-proxy-b2 sh -c "grep Cap /proc/self/status"
docker exec nexis-web-session-b sh -c "grep Cap /proc/self/status"
```

For all four containers, the reported output was:

```text
CapInh: 0000000000000000
CapPrm: 0000000000000000
CapEff: 0000000000000000
CapBnd: 0000000000000000
CapAmb: 0000000000000000
```

| Container | Runtime capability sets | Assessment |
|---|---|---|
| `nexis-proxy-a2` | All zero | PASS — checked process |
| `nexis-web-session-a` | All zero | PASS — checked process |
| `nexis-proxy-b2` | All zero | PASS — checked process |
| `nexis-web-session-b` | All zero | PASS — checked process |

**Interpretation:** `HostConfig.CapDrop=["ALL"]` is a configured restriction. The `/proc/self/status` checks show the capabilities of the specific process executed by `docker exec` at test time. They do not constitute a complete audit of every process or kernel isolation mechanism.

## 4. Limitations and security interpretation

1. **Local-only environment:** All tests ran on one computer using Windows PowerShell and Docker Desktop. Host-facing endpoints were bound to `127.0.0.1` only; access from another computer was not tested.
2. **HTTP client used:** HTTP tests used `curl.exe`, not a web browser. No browser-based user journey was verified.
3. **Scope of isolation evidence:** Direct-IP connections between the tested A/B container pairs timed out in both directions, and cross-session DNS lookups failed. Same-session TCP connectivity from A2 to Web A succeeded. This supports isolation in the observed Docker setup, but does not prove Docker security generally or rule out every lateral-movement path.
4. **Timeout interpretation:** `TimeoutError` shows that a TCP connection did not complete within the timeout. It does not by itself identify the packet-drop or firewall mechanism. Packet captures and firewall/routing inspection were not carried out.
5. **Prototype reverse proxy:** The proxy uses the Python standard library and is a demonstration component, not a production-ready security gateway. Real student use requires production-grade HTTP handling, access control, and backend-mediated session authentication and authorization.
6. **Upstream trust boundary:** `NEXIS_UPSTREAM_HOST` is supplied at container creation. In a deployed system, only trusted backend logic should derive it from session ownership or metadata; it must not come from untrusted student requests.
7. **Shared demo flag:** Both sessions received `NEXIS{web_recon_basics}`. The flag is hardcoded and identical by design for this connectivity demonstration. It is unsuitable for graded assessment, independent student scoring, or anti-cheating enforcement.
8. **Configuration vs runtime:** `HostConfig` records the requested restrictions. The capability checks show only the capability sets of the checked process. Neither alone establishes holistic security.
9. **Remaining tests:** The `Internal` flag for `nexis-session-a`, non-`GET` HTTP method filtering on v2, lifecycle cleanup, authenticated session ownership, and individual flag validation remain unverified. Path handling on v2 was tested for the five requests in Section 2.1.

## 5. Conclusion and status

**Local prototype result: PASS for the specified tests, with T06 limited to TCP connectivity verification.** These results demonstrate the observed behaviour in the local Docker environment and do not establish production-level security.

Both v2 proxies returned the demo flag over HTTP from localhost (T01, T07). Cross-session TCP attempts by direct IP timed out in both directions (T04, T05), cross-session DNS lookups failed (T02, T03), and same-session TCP connectivity from A2 to Web A succeeded (T06). Security configuration for all four containers matched the intended restrictions, and the five capability sets were zero in each container.

**Follow-up status:**

- [x] Correct A2 startup configuration and re-test HTTP on port 8083 (200 OK), evidence: T07.
- [x] Confirm B2 HTTP on port 8084 (200 OK), evidence: T01.
- [x] Test direct-IP cross-session connectivity in both directions (both timed out), evidence: T04, T05.
- [x] Review HostConfig restrictions for all four containers, evidence: Section 3 inspection output.
- [x] Check five Linux capability sets inside all four containers (all zero), evidence: Section 3.1 command output.
- [ ] Independently confirm `docker network inspect nexis-session-a --format '{{.Internal}}'`.
- [x] Observe canonical and variant-path handling on the final v2 A2 proxy, evidence: T08–T12 and proxy logs.
- [ ] Re-test rejected non-`GET` HTTP methods on the final v2 proxies.
- [ ] Integrate and test backend-controlled authentication, authorization, lifecycle cleanup, and individual flag validation.
- [ ] Evaluate production-grade proxy and deployment hardening before use beyond the local demo.

**Git status:** This report documents tests only. No commit or push is claimed or performed.
