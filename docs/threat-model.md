# Threat model (STRIDE)

Scope: the path from a commit to a running pod. Assets: source code, CI credentials, the
container image, runtime secrets and the cluster.

| Threat | Example | Control in this repository |
|---|---|---|
| **Spoofing** | Someone pushes an image that looks like ours | Cosign keyless signature bound to this repo's workflow on `main`; Kyverno `verify-image-signatures` in [platform-gitops](https://github.com/Engdarwish2019/platform-gitops) rejects anything else |
| **Tampering** | Image changed after the scan | Signing and SLSA provenance are tied to the **digest**; Kyverno pins tags to the verified digest at admission |
| **Tampering** | Vulnerable dependency pulled in | `pip-audit`, Trivy image scan, pinned versions, Dependabot for pip, Docker and Actions (7-day cooldown before a new release is proposed) |
| **Tampering** | A third-party GitHub Action's tag is moved to malicious code | Every action is pinned to a full commit SHA (version kept as a comment for Dependabot); Semgrep fails the build on any mutable tag |
| **Repudiation** | "Who built this?" | GitHub build provenance attestation and Rekor transparency log entries for every signature |
| **Information disclosure** | Secrets committed or baked into the image | gitleaks on full history, no secrets in the image or in Kubernetes Secrets: Vault Agent injection with Kubernetes auth, CI reads Vault through OIDC |
| **Information disclosure** | Server leaks stack details | No server header, API docs disabled, strict security headers, verified by ZAP |
| **Denial of service** | Unbounded input or memory use | Input length and pattern validation, item cap, memory limits in Kubernetes |
| **Elevation of privilege** | Container breakout or lateral movement | Non-root UID 10001, read-only root filesystem, all capabilities dropped, seccomp `RuntimeDefault`, Pod Security `restricted`, default-deny NetworkPolicy, Falco rules for shells, package managers and unexpected connections |
| **Elevation of privilege** | Over-privileged CI token | Workflow `permissions: contents: read` by default, write scopes only on the job that needs them, no long-lived cloud or registry credentials |
