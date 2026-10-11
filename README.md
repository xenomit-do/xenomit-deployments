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

## Signed image promotion

`.github/workflows/promote-image.yml` receives `workflow_dispatch` requests from
the per-repo source workflows (runs on `xenomit-platform`) and opens a PR that
updates only the image digest:

* `orchestrator` -> `apps/control-plane/kustomization.yaml` (kustomize `images[].digest`)
* `web-panel` -> `apps/panel/kustomization.yaml`
* `botd` -> `fleet/botd-image.json` (created if absent)

### Dispatch contract

Source workflows (on `xenomit-build`, `main` only) build, push, and keyless-sign
(cosign v2.4.3, buildx provenance+SBOM, tag = `GITHUB_SHA`, OCI source/revision
labels), then mint a GitHub App installation token with **Actions: write only**
and call this workflow's `workflow_dispatch` endpoint on `main` with:

```json
{
  "ref": "main",
  "inputs": {
    "image": "orchestrator|web-panel|botd",
    "digest": "sha256:<64 lowercase hex>",
    "source_repository": "xenomit-do/<repo>",
    "source_sha": "<40 lowercase hex>"
  }
}
```

`scripts/promote_image.py` strictly validates the allowlisted
image -> source repository mapping, digest format, and SHA format; mismatches fail
the run. Duplicate digests no-op with no PR. The promotion branch, commit, and PR
are made via the GitHub REST API using a short-lived installation token. This
ensures the resulting PR triggers normal required checks; the workflow's own
`GITHUB_TOKEN` is read-only and used only for checkout.

### Required GitHub App configuration

* One GitHub App installed **only** on `xenomit-do/xenomit-deployments` with
  **Actions: write, Contents: write, Pull requests: write**.
* Source workflows request an installation token with **Actions: write only**
  and dispatch this one workflow. The deployments workflow separately mints a
  token with **Contents: write, Pull requests: write** to make its digest PR.
* `APP_ID` and `APP_PRIVATE_KEY` are **organization secrets restricted to the
  three image source repos and xenomit-deployments**. Source workflows cannot
  write deployment files directly; branch protection and required checks still
  govern the promotion PR.

### Transition from the old platform token

The previous flow used a long-lived platform PAT. Install the App and scope the
org secrets as above; after the external runner-group and services-policy IaC
changes are applied, the source workflows can dispatch promotions. Then revoke
the old platform token and remove the legacy platform promotion job.
