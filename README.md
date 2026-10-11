# xenomit-deployments

Deployment sources that Argo CD syncs from.

This repository is created by `xenomit-platform/bootstrap/2-seed` with the `gitops` admin account. It is **not** part of the platform infrastructure repositories: Atlantis has no access to it. Argo CD reads it with the read-only user `xenomit-argocd`.

## Layout

Nothing is deployed from here yet. The layout to use:

- `apps/<name>/` : one Kustomize directory per deployed application, pinned to image digests.
- `flash-client/` : build context for the botd image. The image workflow in `xenomit-platform` (`ci/workflows/images.yml`) clones `xenomit-deployments/flash-client` and expects a `Dockerfile` there. It is empty until the Flash client moves out of local builds; the artifact source is the GitHub release of `xenomit-flash-client-linux`.

## Changes

`main` is not protected yet. Open a pull request for every change anyway. Protect `main` (and give the CI user a push whitelist) before CI starts promoting image digests into this repository.
