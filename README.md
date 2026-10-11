# Xenomit deployments

Argo CD sources from GitHub, independent of Gitea. OpenTofu in xenomit-platform creates
the projects/applications; Argo owns only objects rendered by this repository.

* runners/build and runners/platform: Helm wrappers around ARC scale sets. Authentication
  Secrets and the ARC controller belong to OpenTofu. Runner count, image, and resources change by PR.
* fleet: desired XenomitBot/BotRollout/Proxy specifications; operator-generated children are not in Git.
* apps: control-plane and panel Kustomize sources. Disabled until valid image digests and application
  credentials are provisioned. Commit promotion PRs before setting enable_applications=true.

Never commit bot credentials. No direct panel/API specification edits in GitOps mode.
Cluster-owned ServiceAccounts/RBAC for the operator are provisioned by OpenTofu.
