# GitHub Actions (main branch of this repository only) may read CI secrets.
path "secret/data/ci/devsecops-pipeline/*" {
  capabilities = ["read"]
}
