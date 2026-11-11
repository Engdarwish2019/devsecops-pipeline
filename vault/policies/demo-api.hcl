# Read-only access to the demo-api configuration. Nothing else.
path "secret/data/demo-api/*" {
  capabilities = ["read"]
}
