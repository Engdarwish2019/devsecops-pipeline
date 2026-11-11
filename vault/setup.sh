#!/usr/bin/env bash
# Configure Vault for this project. Needs VAULT_ADDR and an admin token in the environment.
#  - KV v2 secrets engine
#  - Kubernetes auth: the demo-api service account reads its own config
#  - JWT auth for GitHub Actions OIDC: CI reads secrets without any stored token
set -euo pipefail

: "${VAULT_ADDR:?set VAULT_ADDR}"
here="$(cd "$(dirname "$0")" && pwd)"

vault secrets enable -path=secret kv-v2 2>/dev/null || echo "kv-v2 already enabled at secret/"

vault policy write demo-api "$here/policies/demo-api.hcl"
vault policy write ci "$here/policies/ci.hcl"

# Kubernetes auth (run from a machine whose kubeconfig points at the cluster)
vault auth enable kubernetes 2>/dev/null || echo "kubernetes auth already enabled"
vault write auth/kubernetes/config \
  kubernetes_host="$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.server}')"
vault write auth/kubernetes/role/demo-api \
  bound_service_account_names=demo-api \
  bound_service_account_namespaces=demo-api \
  policies=demo-api \
  ttl=1h

# GitHub Actions OIDC
vault auth enable jwt 2>/dev/null || echo "jwt auth already enabled"
vault write auth/jwt/config \
  oidc_discovery_url="https://token.actions.githubusercontent.com" \
  bound_issuer="https://token.actions.githubusercontent.com"
vault write auth/jwt/role/ci - <<JSON
{
  "role_type": "jwt",
  "user_claim": "actor",
  "bound_audiences": ["https://github.com/Engdarwish2019"],
  "bound_claims": {
    "repository": "Engdarwish2019/devsecops-pipeline",
    "ref": "refs/heads/main"
  },
  "policies": ["ci"],
  "ttl": "10m"
}
JSON

echo "Vault configured. Store app config with:"
echo "  vault kv put secret/demo-api/config database_url='postgres://...'"
