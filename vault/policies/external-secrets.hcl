# External Secrets Operator in platform-gitops: read platform secrets (for example the
# Grafana admin login at secret/platform/grafana) and nothing else.
path "secret/data/platform/*" {
  capabilities = ["read"]
}
