# Desired fleet

Add XenomitBot, BotRollout, and Proxy manifests to kustomization.yaml through GitHub PRs.
Argo owns their specifications; the operator owns status, finalizers, and generated workloads.
Credentials are runtime inputs, never Git data. Start with desiredState: stopped until credentials
and pinned images exist. Delete manifests through PRs to remove bots; do not edit specs through the panel.
